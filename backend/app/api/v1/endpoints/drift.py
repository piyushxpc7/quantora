from fastapi import APIRouter, HTTPException, Body, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.drift_detection_service import DriftDetectionService
from app.core.database import get_db
from app.repositories.drift_repo import save_drift_report, list_drift_reports

router = APIRouter()
drift_service = DriftDetectionService()


@router.post("/analyze")
async def analyze_drift(
    reference_data: List[float] = Body(...),
    current_data: List[float] = Body(...),
    feature_name: str = Body("default"),
    db: AsyncSession = Depends(get_db),
):
    if len(reference_data) < 10 or len(current_data) < 10:
        raise HTTPException(status_code=400, detail="Insufficient data points (min 10)")

    result = drift_service.detect_drift_statistical(reference_data, current_data)
    await save_drift_report(db, result, feature_name)
    return result


@router.post("/train-model")
def train_model(data: List[List[float]] = Body(...)):
    import numpy as np
    try:
        np_data = np.array(data)
        if np_data.ndim != 2:
            raise HTTPException(status_code=400, detail="Data must be 2D array")
        return drift_service.train_autoencoder(np_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-anomalies")
def detect_anomalies(data: List[List[float]] = Body(...)):
    import numpy as np
    try:
        np_data = np.array(data)
        result = drift_service.detect_anomalies_autoencoder(np_data)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_drift_history(db: AsyncSession = Depends(get_db)):
    reports = await list_drift_reports(db, limit=30)
    return [
        {
            "id": r.id,
            "feature_name": r.feature_name,
            "psi_value": r.psi_value,
            "ks_statistic": r.ks_statistic,
            "ks_p_value": r.ks_p_value,
            "overall_drift": r.overall_drift,
            "severity": r.severity,
            "timestamp": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]


@router.get("/summary")
async def get_drift_summary(db: AsyncSession = Depends(get_db)):
    reports = await list_drift_reports(db, limit=100)
    if not reports:
        return {"latest_psi": None, "latest_ks_p_value": None, "alert_count": 0, "total_checks": 0}

    latest = reports[0]
    alerts = sum(1 for r in reports if r.overall_drift)
    return {
        "latest_psi": latest.psi_value,
        "latest_ks_p_value": latest.ks_p_value,
        "latest_severity": latest.severity,
        "alert_count": alerts,
        "total_checks": len(reports),
    }
