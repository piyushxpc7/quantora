"""
Background regime-monitoring scheduler.

Every `MONITOR_INTERVAL_MINUTES` it runs a drift check on each active monitored strategy
(raising alerts on regime shift) and rebalances the paper account toward the most robust
active strategy. Runs in-process via asyncio; safe to disable (no-op if DB unavailable).
"""
import asyncio
from typing import Optional
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.repositories import monitoring_repo, paper_repo
from sqlalchemy import select
from app.models.monitoring import MonitoredStrategy

_task: Optional[asyncio.Task] = None


async def _tick():
    async with AsyncSessionLocal() as db:
        checked = await monitoring_repo.check_all_active(db)
        # Rebalance paper into the highest-honesty active strategy.
        strategies = (await db.execute(
            select(MonitoredStrategy).where(MonitoredStrategy.active == True)  # noqa: E712
        )).scalars().all()
        if strategies:
            best = max(strategies, key=lambda s: s.honesty_score or 0)
            try:
                await paper_repo.rebalance(db, best.id)
            except Exception:
                pass
        return checked


async def _loop():
    interval = max(60, settings.MONITOR_INTERVAL_MINUTES * 60)
    while True:
        try:
            await _tick()
        except Exception as e:
            print(f"[scheduler] tick error: {e}")
        await asyncio.sleep(interval)


def start_scheduler():
    global _task
    if _task is None:
        _task = asyncio.create_task(_loop())
        print(f"[scheduler] monitoring every {settings.MONITOR_INTERVAL_MINUTES} min")


async def stop_scheduler():
    global _task
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except (asyncio.CancelledError, Exception):
            pass
        _task = None
