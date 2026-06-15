from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.workflow import WorkflowRun


def _clean_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Trim the event log for storage: drop the heavy/self-referential 'complete' payload
    and the bulky tool_result 'data' blobs (keep the narrative + compact summaries)."""
    clean = []
    for ev in events or []:
        t = ev.get("type")
        if t in ("complete", "saved", "save_error"):
            continue
        if t == "tool_result":
            clean.append({"type": t, "tool": ev.get("tool"), "summary": ev.get("summary")})
        else:
            clean.append(ev)
    return clean


async def save_workflow(db: AsyncSession, user_request: str, result: Dict[str, Any]) -> WorkflowRun:
    """Persist a research run produced by the agentic runtime (agent_runtime.assemble_result)."""
    backtest = result.get("backtest", {}) or {}
    params = result.get("strategy", {}) or {}
    metrics = backtest.get("metrics", {}) or {}
    honesty = result.get("honesty", {}) or {}
    portfolio = result.get("portfolio", {}) or {}
    robustness = backtest.get("robustness", {}) or {}
    recommendation = result.get("recommendation")

    run = WorkflowRun(
        user_request=user_request,
        strategy_name=params.get("strategy_name") or f"{params.get('signal_type', 'strategy')} on {', '.join(params.get('universe', [])[:3])}",
        universe=params.get("universe"),
        signal_type=params.get("signal_type"),
        cagr=metrics.get("cagr"),
        sharpe_ratio=metrics.get("sharpe_ratio"),
        max_drawdown=metrics.get("max_drawdown"),
        var_95=metrics.get("var_95"),
        cvar_95=metrics.get("cvar_95"),
        risk_approved=(recommendation == "approve"),
        honesty_score=honesty.get("score"),
        verdict=honesty.get("verdict"),
        recommendation=recommendation,
        oos_sharpe=backtest.get("metrics_oos", {}).get("sharpe_ratio"),
        pbo=robustness.get("pbo", {}).get("pbo"),
        final_allocation=portfolio.get("weights"),
        optimization_method=portfolio.get("method"),
        is_monitored=False,
        workflow_log=_clean_events(result.get("events", [])),
        status=result.get("status", "completed"),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def list_workflows(db: AsyncSession, limit: int = 20) -> List[WorkflowRun]:
    result = await db.execute(select(WorkflowRun).order_by(desc(WorkflowRun.created_at)).limit(limit))
    return list(result.scalars().all())


async def get_dashboard_stats(db: AsyncSession) -> Dict[str, Any]:
    runs = await list_workflows(db, limit=100)
    approved = [r for r in runs if r.risk_approved]
    latest_pnl = approved[0].cagr if approved else 0.0
    honesty_vals = [r.honesty_score for r in runs if r.honesty_score is not None]
    return {
        "total_strategies": len(runs),
        "approved_strategies": len(approved),
        "monitored_strategies": len([r for r in runs if getattr(r, "is_monitored", False)]),
        "latest_cagr": latest_pnl,
        "avg_sharpe": sum(r.sharpe_ratio for r in approved if r.sharpe_ratio) / max(len(approved), 1),
        "avg_honesty": round(sum(honesty_vals) / len(honesty_vals), 1) if honesty_vals else None,
        "overfit_rejected": len([r for r in runs if r.verdict == "Likely Overfit"]),
    }
