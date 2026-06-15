import numpy as np
import pandas as pd
from typing import Dict, Any


def compute_metrics(returns: pd.Series, risk_free_rate: float = 0.04) -> Dict[str, Any]:
    """Compute performance and risk metrics from a daily returns series."""
    if returns.empty or len(returns) < 2:
        return {}

    n = len(returns)
    ann_factor = 252

    # Performance
    total_return = (1 + returns).prod() - 1
    cagr = (1 + total_return) ** (ann_factor / n) - 1
    ann_vol = returns.std() * np.sqrt(ann_factor)
    sharpe = (returns.mean() * ann_factor - risk_free_rate) / (ann_vol + 1e-9)

    # Sortino (downside deviation)
    downside = returns[returns < 0]
    sortino_denom = downside.std() * np.sqrt(ann_factor) if len(downside) > 1 else 1e-9
    sortino = (returns.mean() * ann_factor - risk_free_rate) / sortino_denom

    # Drawdown
    equity = (1 + returns).cumprod()
    peak = equity.cummax()
    drawdown = (equity - peak) / peak
    max_drawdown = drawdown.min()

    # VaR & CVaR (historical, 95% confidence)
    var_95 = float(np.percentile(returns, 5))
    cvar_95 = float(returns[returns <= var_95].mean())

    calmar = float(cagr / abs(max_drawdown)) if max_drawdown < -1e-9 else 0.0

    return {
        "cagr": round(float(cagr), 4),
        "total_return": round(float(total_return), 4),
        "annual_volatility": round(float(ann_vol), 4),
        "sharpe_ratio": round(float(sharpe), 3),
        "sortino_ratio": round(float(sortino), 3),
        "calmar_ratio": round(calmar, 3),
        "max_drawdown": round(float(max_drawdown), 4),
        "var_95": round(var_95, 4),
        "cvar_95": round(cvar_95, 4),
        "num_trading_days": n,
    }


def compute_benchmark_stats(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
    risk_free_rate: float = 0.04,
) -> Dict[str, Any]:
    """Alpha, beta, information ratio and a 'beats benchmark' flag vs a benchmark series."""
    df = pd.concat([strategy_returns, benchmark_returns], axis=1, keys=["s", "b"]).dropna()
    if len(df) < 5 or df["b"].std() < 1e-12:
        return {}

    s, b = df["s"].values, df["b"].values
    ann_factor = 252
    # CAPM-style beta/alpha via covariance
    beta = float(np.cov(s, b)[0, 1] / (np.var(b) + 1e-12))
    alpha_daily = float(s.mean() - beta * b.mean())
    alpha_ann = alpha_daily * ann_factor

    active = s - b
    te = active.std() * np.sqrt(ann_factor)  # tracking error
    info_ratio = float(active.mean() * ann_factor / (te + 1e-12))

    strat_sharpe = (s.mean() * ann_factor - risk_free_rate) / (s.std() * np.sqrt(ann_factor) + 1e-9)
    bench_sharpe = (b.mean() * ann_factor - risk_free_rate) / (b.std() * np.sqrt(ann_factor) + 1e-9)

    return {
        "alpha_annual": round(alpha_ann, 4),
        "beta": round(beta, 3),
        "information_ratio": round(info_ratio, 3),
        "tracking_error": round(float(te), 4),
        "benchmark_sharpe": round(float(bench_sharpe), 3),
        "beats_benchmark": bool(strat_sharpe > bench_sharpe),
    }
