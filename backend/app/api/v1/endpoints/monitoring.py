from fastapi import APIRouter, HTTPException, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.monitoring import MonitoredStrategy
from sqlalchemy import select
from app.repositories import monitoring_repo as repo

router = APIRouter()


def _serialize(s: MonitoredStrategy) -> dict:
    return {
        "id": s.id,
        "run_id": s.run_id,
        "name": s.name,
        "universe": s.universe or [],
        "signal_type": s.signal_type,
        "honesty_score": s.honesty_score,
        "latest_psi": s.latest_psi,
        "regime_status": s.regime_status,
        "active": s.active,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "last_checked": s.last_checked.isoformat() if s.last_checked else None,
    }


@router.post("/monitor")
async def promote(run_id: int = Body(..., embed=True), db: AsyncSession = Depends(get_db)):
    strat = await repo.promote_run(db, run_id)
    if strat is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    # immediate first check so the UI shows a status right away
    await repo.run_check(db, strat)
    await db.refresh(strat)
    return _serialize(strat)


@router.get("/monitored")
async def monitored(db: AsyncSession = Depends(get_db)):
    return [_serialize(s) for s in await repo.list_monitored(db)]


@router.get("/alerts")
async def alerts(db: AsyncSession = Depends(get_db)):
    return [
        {
            "id": a.id,
            "strategy_id": a.strategy_id,
            "strategy_name": a.strategy_name,
            "psi_value": a.psi_value,
            "ks_p_value": a.ks_p_value,
            "severity": a.severity,
            "message": a.message,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in await repo.list_alerts(db)
    ]


@router.post("/monitored/{strategy_id}/check")
async def check_one(strategy_id: int, db: AsyncSession = Depends(get_db)):
    strat = (await db.execute(
        select(MonitoredStrategy).where(MonitoredStrategy.id == strategy_id)
    )).scalar_one_or_none()
    if strat is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return await repo.run_check(db, strat)


@router.post("/monitored/{strategy_id}/stop")
async def stop_one(strategy_id: int, db: AsyncSession = Depends(get_db)):
    ok = await repo.stop(db, strategy_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"stopped": True}
