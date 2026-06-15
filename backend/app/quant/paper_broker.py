"""
In-process paper broker (no real money, no external broker).

A single paper account is rebalanced to a strategy's target weights. Every rebalance passes
through a real risk gate: we estimate the target portfolio's 95% CVaR from recent returns and
*block* the rebalance if it breaches `RISK_CVAR_LIMIT` — exactly the kind of pre-trade control
a desk would enforce. Blocked attempts are recorded so the UI can show them.
"""
from __future__ import annotations

from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from app.core.config import settings
from app.services.market_data_service import MarketDataService


def latest_prices(tickers: List[str]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for t in tickers:
        p = MarketDataService.get_latest_price(t)
        if p:
            out[t] = float(p)
    return out


def portfolio_cvar(weights: Dict[str, float], confidence: float = 0.95) -> float:
    """Historical 95% CVaR of the weighted portfolio from ~6mo of daily returns (a loss, negative)."""
    series = {}
    for t, w in weights.items():
        raw = MarketDataService.fetch_historical_data(t, period="6mo", interval="1d")
        if "error" in raw or not raw.get("data"):
            continue
        df = pd.DataFrame(raw["data"])
        if "Close" in df.columns:
            series[t] = df["Close"].astype(float).pct_change().dropna().reset_index(drop=True)
    if not series:
        return 0.0
    rets = pd.DataFrame(series).dropna()
    if rets.empty:
        return 0.0
    w = np.array([weights.get(c, 0.0) for c in rets.columns])
    w = w / (w.sum() + 1e-12)
    port = rets.values @ w
    var = np.percentile(port, (1 - confidence) * 100)
    cvar = port[port <= var].mean() if np.any(port <= var) else var
    return float(cvar)


def risk_check(weights: Dict[str, float]) -> Tuple[bool, float]:
    """Return (approved, cvar). Approved when |CVaR| within the configured limit."""
    cvar = portfolio_cvar(weights)
    return abs(cvar) <= settings.RISK_CVAR_LIMIT, cvar


def compute_target_shares(weights: Dict[str, float], equity: float, prices: Dict[str, float]) -> Dict[str, float]:
    target: Dict[str, float] = {}
    for t, w in weights.items():
        px = prices.get(t)
        if px and px > 0:
            target[t] = round((equity * w) / px, 4)
    return target
