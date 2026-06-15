import json
from fastapi import APIRouter, HTTPException, Body, Depends
from fastapi.responses import StreamingResponse
from starlette.concurrency import iterate_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.manager import AgentManager
from app.core.database import get_db, AsyncSessionLocal
from app.repositories.workflow_repo import save_workflow, list_workflows, get_dashboard_stats

router = APIRouter()
manager = AgentManager()


@router.post("/workflow")
async def run_agent_workflow(
    request: str = Body(..., embed=True, description="User request for trading strategy"),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = manager.run_workflow(request)
        await save_workflow(db, request, result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflow/stream")
async def stream_agent_workflow(
    request: str = Body(..., embed=True, description="User request for trading strategy"),
):
    """Server-Sent Events stream of the agentic research run (thought/tool_call/verdict)."""

    async def event_gen():
        events = []
        final_result = None
        try:
            async for ev in iterate_in_threadpool(manager.stream_workflow(request)):
                events.append(ev)
                if ev.get("type") == "complete":
                    final_result = ev.get("result")
                yield f"data: {json.dumps(ev)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        # Persist after the stream finishes (best-effort).
        if final_result is not None:
            try:
                final_result["events"] = events
                async with AsyncSessionLocal() as db:
                    run = await save_workflow(db, request, final_result)
                    yield f"data: {json.dumps({'type': 'saved', 'run_id': run.id})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'save_error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.get("/runs")
async def get_workflow_runs(db: AsyncSession = Depends(get_db)):
    runs = await list_workflows(db)
    return [
        {
            "id": r.id,
            "user_request": r.user_request,
            "strategy_name": r.strategy_name,
            "universe": r.universe,
            "cagr": r.cagr,
            "sharpe_ratio": r.sharpe_ratio,
            "oos_sharpe": r.oos_sharpe,
            "max_drawdown": r.max_drawdown,
            "risk_approved": r.risk_approved,
            "honesty_score": r.honesty_score,
            "verdict": r.verdict,
            "recommendation": r.recommendation,
            "pbo": r.pbo,
            "is_monitored": r.is_monitored,
            "final_allocation": r.final_allocation,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    return await get_dashboard_stats(db)
