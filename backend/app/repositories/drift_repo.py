from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.drift import DriftReport


async def save_drift_report(db: AsyncSession, result: Dict[str, Any], feature_name: str = "default") -> DriftReport:
    ks = result.get("ks_test", {})
    psi = result.get("psi", {})

    psi_val = psi.get("value", 0.0)
    severity = "low"
    if psi_val >= 0.2:
        severity = "high"
    elif psi_val >= 0.1:
        severity = "medium"

    report = DriftReport(
        feature_name=feature_name,
        ks_statistic=ks.get("statistic"),
        ks_p_value=ks.get("p_value"),
        ks_drift=ks.get("drift_detected"),
        psi_value=psi_val,
        psi_drift=psi.get("drift_detected"),
        overall_drift=result.get("overall_drift"),
        severity=severity,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def list_drift_reports(db: AsyncSession, limit: int = 30) -> List[DriftReport]:
    result = await db.execute(select(DriftReport).order_by(desc(DriftReport.created_at)).limit(limit))
    return list(result.scalars().all())
