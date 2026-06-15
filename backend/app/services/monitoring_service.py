"""
Regime-monitoring helpers — ties the drift engine to live strategies.

We snapshot a strategy's "normal" return distribution at promotion time, then periodically
compare the most recent market window against it with the same KS + PSI engine used in the
Drift Lab. A divergence means the live regime has drifted away from what the strategy was
validated on — the early-warning signal that a strategy is decaying.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
import pandas as pd

from app.services.market_data_service import MarketDataService
from app.services.drift_detection_service import DriftDetectionService

RECENT_WINDOW = 60


def _returns(ticker: str, period: str = "2y") -> List[float]:
    raw = MarketDataService.fetch_historical_data(ticker, period=period, interval="1d")
    if "error" in raw or not raw.get("data"):
        return []
    df = pd.DataFrame(raw["data"])
    if "Close" not in df.columns:
        return []
    return df["Close"].astype(float).pct_change().dropna().tolist()


def build_reference(universe: List[str]) -> List[float]:
    """Pooled returns for the universe, excluding the most recent window (the 'normal' regime)."""
    ref: List[float] = []
    for t in (universe or [])[:5]:
        r = _returns(t)
        if len(r) > RECENT_WINDOW + 60:
            ref.extend(r[:-RECENT_WINDOW])
    return ref


def current_window(universe: List[str]) -> List[float]:
    cur: List[float] = []
    for t in (universe or [])[:5]:
        r = _returns(t, period="6mo")
        if len(r) >= RECENT_WINDOW:
            cur.extend(r[-RECENT_WINDOW:])
    return cur


def assess_regime(reference: List[float], current: List[float]) -> Optional[Dict[str, Any]]:
    if len(reference) < 30 or len(current) < 30:
        return None
    res = DriftDetectionService.detect_drift_statistical(reference, current)
    psi = res["psi"]["value"]
    ks_p = res["ks_test"]["p_value"]
    if psi >= 0.2:
        status, severity = "shifted", "high"
    elif psi >= 0.1:
        status, severity = "watch", "medium"
    else:
        status, severity = "ok", "low"
    return {
        "psi": round(float(psi), 4),
        "ks_p_value": round(float(ks_p), 4),
        "regime_shift": bool(res["overall_drift"]),
        "status": status,
        "severity": severity,
    }
