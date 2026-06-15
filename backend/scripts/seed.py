"""
Seed script — populates DB with sample workflow runs and drift reports so the demo
looks alive on first load.

Usage:
  cd backend && python -m scripts.seed
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal, create_tables
import app.models  # noqa: registers models

from app.models.workflow import WorkflowRun
from app.models.drift import DriftReport


async def seed():
    await create_tables()

    async with AsyncSessionLocal() as db:
        # Sample workflow runs
        runs = [
            WorkflowRun(
                user_request="Momentum strategy on AAPL, MSFT, GOOGL",
                strategy_name="Tech Momentum",
                universe=["AAPL", "MSFT", "GOOGL"],
                signal_type="momentum",
                cagr=0.142,
                sharpe_ratio=1.71,
                max_drawdown=-0.118,
                var_95=-0.021,
                cvar_95=-0.031,
                risk_approved=True,
                honesty_score=74.0, verdict="Robust", recommendation="approve",
                oos_sharpe=1.32, pbo=0.14, is_monitored=False,
                final_allocation={"AAPL": 0.38, "MSFT": 0.35, "GOOGL": 0.27},
                optimization_method="hrp",
                status="completed",
            ),
            WorkflowRun(
                user_request="Mean reversion on Energy sector",
                strategy_name="Energy Mean Reversion",
                universe=["XOM", "CVX", "COP"],
                signal_type="mean_reversion",
                cagr=0.089,
                sharpe_ratio=1.23,
                max_drawdown=-0.152,
                var_95=-0.028,
                cvar_95=-0.041,
                risk_approved=True,
                honesty_score=52.0, verdict="Fragile", recommendation="approve",
                oos_sharpe=0.61, pbo=0.38, is_monitored=False,
                final_allocation={"XOM": 0.42, "CVX": 0.35, "COP": 0.23},
                optimization_method="hrp",
                status="completed",
            ),
            WorkflowRun(
                user_request="Aggressive momentum on small caps",
                strategy_name="Small Cap Momentum",
                universe=["GME", "AMC", "BBBY"],
                signal_type="momentum",
                cagr=-0.031,
                sharpe_ratio=-0.42,
                max_drawdown=-0.612,
                var_95=-0.089,
                cvar_95=-0.134,
                risk_approved=False,
                honesty_score=18.0, verdict="Likely Overfit", recommendation="reject",
                oos_sharpe=-1.1, pbo=0.81, is_monitored=False,
                final_allocation=None,
                optimization_method=None,
                status="completed",
            ),
        ]
        for r in runs:
            db.add(r)

        # Sample drift reports
        drift_data = [
            (0.04, 0.71, False, "low"),
            (0.07, 0.44, False, "low"),
            (0.11, 0.18, True, "medium"),
            (0.09, 0.29, False, "low"),
            (0.23, 0.02, True, "high"),
            (0.18, 0.06, True, "medium"),
            (0.13, 0.15, True, "medium"),
        ]
        for psi, ks_p, drift, sev in drift_data:
            db.add(DriftReport(
                feature_name="returns_feature",
                ks_statistic=round(0.3 - ks_p * 0.2, 3),
                ks_p_value=ks_p,
                ks_drift=ks_p < 0.05,
                psi_value=psi,
                psi_drift=psi >= 0.2,
                overall_drift=drift,
                severity=sev,
            ))

        await db.commit()
        print("Seed complete: 3 workflow runs, 7 drift reports inserted.")


if __name__ == "__main__":
    asyncio.run(seed())
