import pandas as pd
import numpy as np
from typing import Dict, List, Any
from app.services.market_data_service import MarketDataService

try:
    from pypfopt import EfficientFrontier, risk_models, expected_returns, HRPOpt
    _pypfopt_available = True
except ImportError:
    _pypfopt_available = False


def _fallback_equal_weight(universe: List[str]) -> Dict[str, float]:
    w = round(1.0 / len(universe), 4)
    return {t: w for t in universe}


def optimize_portfolio(universe: List[str], method: str = "hrp", period: str = "1y") -> Dict[str, Any]:
    """
    Returns optimal portfolio weights using HRP or Mean-Variance.
    Falls back to equal-weight if PyPortfolioOpt is not installed or data is insufficient.
    """
    prices = {}
    for ticker in universe[:8]:
        raw = MarketDataService.fetch_historical_data(ticker, period=period, interval="1d")
        if "error" in raw or not raw.get("data"):
            continue
        df = pd.DataFrame(raw["data"])
        if "Close" in df.columns:
            df["Close"] = df["Close"].astype(float)
            prices[ticker] = df["Close"].values

    if len(prices) < 2:
        weights = _fallback_equal_weight(universe)
        return {"weights": weights, "method": "equal_weight", "note": "Insufficient data"}

    min_len = min(len(v) for v in prices.values())
    price_df = pd.DataFrame({k: v[-min_len:] for k, v in prices.items()})

    if not _pypfopt_available or len(price_df) < 30:
        weights = _fallback_equal_weight(list(price_df.columns))
        return {"weights": weights, "method": "equal_weight", "note": "PyPortfolioOpt unavailable or insufficient history"}

    try:
        if method == "hrp":
            returns = price_df.pct_change().dropna()
            hrp = HRPOpt(returns)
            raw_weights = hrp.optimize()
            weights = {k: round(float(v), 4) for k, v in raw_weights.items() if v > 0.001}
            return {"weights": weights, "method": "hrp", "expected_annual_return": None}
        else:
            mu = expected_returns.mean_historical_return(price_df)
            S = risk_models.sample_cov(price_df)
            ef = EfficientFrontier(mu, S)
            ef.max_sharpe()
            cleaned = ef.clean_weights()
            weights = {k: round(float(v), 4) for k, v in cleaned.items() if v > 0.001}
            perf = ef.portfolio_performance(verbose=False)
            return {
                "weights": weights,
                "method": "mean_variance_max_sharpe",
                "expected_annual_return": round(perf[0], 4),
                "annual_volatility": round(perf[1], 4),
                "sharpe_ratio": round(perf[2], 3),
            }
    except Exception as e:
        weights = _fallback_equal_weight(list(price_df.columns))
        return {"weights": weights, "method": "equal_weight", "note": str(e)}
