from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict
from app.services.drift_detection_service import DriftDetectionService

router = APIRouter()
drift_service = DriftDetectionService()

@router.post("/analyze")
def analyze_drift(
    reference_data: List[float] = Body(..., description="Historical/Training data"),
    current_data: List[float] = Body(..., description="New/Live data")
):
    """
    Analyze drift between reference data and current data using statistical methods (KS, PSI).
    """
    if len(reference_data) < 10 or len(current_data) < 10:
        raise HTTPException(status_code=400, detail="Insufficient data points for analysis (min 10)")
        
    result = drift_service.detect_drift_statistical(reference_data, current_data)
    return result

@router.post("/train-model")
def train_model(
    data: List[List[float]] = Body(..., description="2D array of training data features")
):
    """
    Train the Autoencoder model on normal data.
    """
    import numpy as np
    try:
        np_data = np.array(data)
        if np_data.ndim != 2:
             raise HTTPException(status_code=400, detail="Data must be 2D array")
             
        result = drift_service.train_autoencoder(np_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/detect-anomalies")
def detect_anomalies(
    data: List[List[float]] = Body(..., description="2D array of new data features")
):
    """
    Detect anomalies in new data using the trained Autoencoder.
    """
    import numpy as np
    try:
        np_data = np.array(data)
        result = drift_service.detect_anomalies_autoencoder(np_data)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
