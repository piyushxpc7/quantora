from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.monitoring import MonitoredStrategy, DriftAlert
from app.models.workflow import WorkflowRun
from app.services import monitoring_service as ms


async def promote_run(db: AsyncSession, run_id: int) -> Optional[MonitoredStrategy]:
    run = (await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))).scalar_one_or_none()
    if run is None:
        return None

    # Avoid duplicates: reactivate if already monitored.
    existing = (await db.execute(
        select(MonitoredStrategy).where(MonitoredStrategy.run_id == run_id)
    )).scalar_one_or_none()
    universe = run.universe or []

    if existing is not None:
        existing.active = True
        run.is_monitored = True
        await db.commit()
        await db.refresh(existing)
        return existing

    reference = ms.build_reference(universe)
    strat = MonitoredStrategy(
        run_id=run.id,
        name=run.strategy_name or f"{run.signal_type} strategy",
        universe=universe,
        signal_type=run.signal_type,
        strategy_params={"signal_type": run.signal_type},
        honesty_score=run.honesty_score,
        reference_returns=reference,
        regime_status="ok",
        active=True,
    )
    run.is_monitored = True
    db.add(strat)
    await db.commit()
    await db.refresh(strat)
    return strat


async def list_monitored(db: AsyncSession) -> List[MonitoredStrategy]:
    res = await db.execute(select(MonitoredStrategy).order_by(desc(MonitoredStrategy.created_at)))
    return list(res.scalars().all())


async def list_alerts(db: AsyncSession, limit: int = 30) -> List[DriftAlert]:
    res = await db.execute(select(DriftAlert).order_by(desc(DriftAlert.created_at)).limit(limit))
    return list(res.scalars().all())


async def run_check(db: AsyncSession, strat: MonitoredStrategy) -> Dict[str, Any]:
    """Run a regime check for one strategy; persist status + raise an alert on a shift."""
    reference = strat.reference_returns or ms.build_reference(strat.universe or [])
    current = ms.current_window(strat.universe or [])
    assessment = ms.assess_regime(reference, current)
    strat.last_checked = datetime.now(timezone.utc)
    if assessment is None:
        await db.commit()
        return {"available": False, "strategy_id": strat.id}

    strat.latest_psi = assessment["psi"]
    strat.regime_status = assessment["status"]

    alerted = False
    if assessment["regime_shift"] or assessment["status"] == "shifted":
        msg = (
            f"Regime shift on {strat.name}: PSI {assessment['psi']:.2f} "
            f"(KS p={assessment['ks_p_value']:.3f}). Live distribution has drifted from the validated regime."
        )
        db.add(DriftAlert(
            strategy_id=strat.id, strategy_name=strat.name,
            psi_value=assessment["psi"], ks_p_value=assessment["ks_p_value"],
            severity=assessment["severity"], message=msg,
        ))
        alerted = True

    await db.commit()
    return {"available": True, "strategy_id": strat.id, "alerted": alerted, **assessment}


async def check_all_active(db: AsyncSession) -> int:
    strategies = (await db.execute(
        select(MonitoredStrategy).where(MonitoredStrategy.active == True)  # noqa: E712
    )).scalars().all()
    count = 0
    for strat in strategies:
        try:
            await run_check(db, strat)
            count += 1
        except Exception:
            continue
    return count


async def stop(db: AsyncSession, strategy_id: int) -> bool:
    strat = (await db.execute(
        select(MonitoredStrategy).where(MonitoredStrategy.id == strategy_id)
    )).scalar_one_or_none()
    if strat is None:
        return False
    strat.active = False
    await db.commit()
    return True
