"""
Honest vectorized backtester.

Unlike a naive in-sample backtest, this engine:
  * charges transaction costs + slippage on every change in exposure (turnover),
  * splits history into in-sample (IS) and out-of-sample (OOS) and reports both,
  * compares against a buy-and-hold benchmark (SPY by default),
  * sweeps the parameter grid so we can measure overfitting (PBO) and parameter fragility,
  * honours the strategy params (lookback, entry/exit thresholds, signal type).

The result feeds `app.quant.robustness.honesty_score` — the platform's headline artifact.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.services.market_data_service import MarketDataService
from app.services.feature_engineering_service import FeatureEngineeringService
from app.quant.metrics import compute_metrics, compute_benchmark_stats
from app.quant import robustness as rb
from app.quant import signals as sig


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def _load_prices(universe: List[str], period: str) -> Dict[str, pd.DataFrame]:
    """Return {ticker: df indexed by date with Close, rsi, returns}."""
    out: Dict[str, pd.DataFrame] = {}
    for ticker in universe[:5]:  # cap for demo speed
        raw = MarketDataService.fetch_historical_data(ticker, period=period, interval="1d")
        if "error" in raw or not raw.get("data"):
            continue
        df = pd.DataFrame(raw["data"])
        if "Close" not in df.columns:
            continue
        df = pd.DataFrame(FeatureEngineeringService.add_technical_indicators(df))
        # normalise a date index
        date_col = next((c for c in ("Date", "Datetime", "index") if c in df.columns), None)
        if date_col is not None:
            df.index = pd.to_datetime(df[date_col])
        df = df.dropna(subset=["Close"])
        df["Close"] = df["Close"].astype(float)
        df["returns"] = df["Close"].pct_change()
        out[ticker] = df[["Close", "rsi", "returns"]]
    return out


def _benchmark_returns(period: str) -> Optional[pd.Series]:
    raw = MarketDataService.fetch_historical_data(settings.BENCHMARK_TICKER, period=period, interval="1d")
    if "error" in raw or not raw.get("data"):
        return None
    df = pd.DataFrame(raw["data"])
    if "Close" not in df.columns:
        return None
    date_col = next((c for c in ("Date", "Datetime", "index") if c in df.columns), None)
    if date_col is not None:
        df.index = pd.to_datetime(df[date_col])
    return df["Close"].astype(float).pct_change().rename("benchmark")


# --------------------------------------------------------------------------- #
# Signal construction (with hysteresis: enter on one band, exit on another)
# --------------------------------------------------------------------------- #
def _hysteresis(entry: pd.Series, exit_: pd.Series) -> pd.Series:
    """1 on entry, 0 on exit, hold in between. Executed next day (shift 1)."""
    pos = pd.Series(np.nan, index=entry.index)
    pos[entry.values] = 1.0
    pos[exit_.values] = 0.0
    pos = pos.ffill().fillna(0.0)
    return pos.shift(1).fillna(0.0)


def _build_signal(df: pd.DataFrame, spec: Dict[str, Any]) -> pd.Series:
    """Evaluate a composable SignalSpec into a next-day position series (with hysteresis)."""
    entry, exit_ = sig.evaluate_spec(df, spec)
    return _hysteresis(entry, exit_)


def _portfolio_returns(prices: Dict[str, pd.DataFrame], spec: Dict[str, Any], cost_per_turn: float):
    """Return (gross_returns, net_returns, signals_df, asset_returns_df), date-aligned."""
    sig_cols, ret_cols, gross_cols, net_cols = {}, {}, {}, {}
    for ticker, df in prices.items():
        position = _build_signal(df, spec)
        ret = df["returns"].fillna(0.0)
        turnover = position.diff().abs().fillna(0.0)
        gross = position * ret
        net = gross - turnover * cost_per_turn
        sig_cols[ticker], ret_cols[ticker] = position, ret
        gross_cols[ticker], net_cols[ticker] = gross, net

    if not net_cols:
        empty = pd.Series(dtype=float)
        return empty, empty, pd.DataFrame(), pd.DataFrame()

    signals_df = pd.DataFrame(sig_cols).fillna(0.0)
    asset_ret_df = pd.DataFrame(ret_cols).fillna(0.0)
    gross_port = pd.DataFrame(gross_cols).fillna(0.0).mean(axis=1)
    net_port = pd.DataFrame(net_cols).fillna(0.0).mean(axis=1)
    return gross_port.dropna(), net_port.dropna(), signals_df, asset_ret_df


def _equity_chart(returns: pd.Series, label: str, tail: int = 90) -> List[Dict[str, Any]]:
    eq = (1 + returns).cumprod().tail(tail)
    return [
        {"date": str(idx.date()) if hasattr(idx, "date") else str(idx), label: round(float(v), 4)}
        for idx, v in eq.items()
    ]


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def run_backtest(
    universe: List[str],
    signal_type: str = "momentum",
    lookback_days: int = 20,
    entry_threshold: float = 0.02,
    exit_threshold: float = -0.01,
    period: str = "3y",
    deep: bool = True,
    signal_spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run an honest backtest. `signal_spec` (a composable SignalSpec) overrides `signal_type`
    when provided. When `deep` is True, also runs the full robustness suite (parameter sweep,
    PBO, deflated Sharpe, permutation test, honesty score).
    """
    cost_per_turn = (settings.TXN_COST_BPS + settings.SLIPPAGE_BPS) / 10_000.0
    prices = _load_prices(universe, period)
    if not prices:
        return {"error": "No data fetched for any ticker in universe"}

    # Build the signal spec (validated). Fall back to a preset if the spec is malformed.
    if signal_spec:
        try:
            spec = sig.validate_spec(signal_spec)
            signal_type = "composite"
        except Exception:
            spec = sig.preset_spec(signal_type, lookback_days, entry_threshold, exit_threshold)
    else:
        spec = sig.preset_spec(signal_type, lookback_days, entry_threshold, exit_threshold)

    gross, net, signals_df, asset_ret_df = _portfolio_returns(prices, spec, cost_per_turn)
    if net.empty:
        return {"error": "No tradable signal produced"}

    exposure = float(signals_df.mean().mean()) if not signals_df.empty else 0.0

    # --- IS / OOS split ---
    split = int(len(net) * (1 - settings.OOS_FRACTION))
    is_net, oos_net = net.iloc[:split], net.iloc[split:]
    metrics_full = compute_metrics(net)
    metrics_is = compute_metrics(is_net)
    metrics_oos = compute_metrics(oos_net)
    gross_metrics = compute_metrics(gross)

    # --- Benchmark ---
    bench = _benchmark_returns(period)
    bench_stats, bench_chart = {}, []
    if bench is not None:
        aligned_bench = bench.reindex(net.index).fillna(0.0)
        bench_stats = compute_benchmark_stats(net, aligned_bench)
        bench_chart = _equity_chart(aligned_bench, "benchmark")

    equity_chart = _equity_chart(net, "value")
    # merge benchmark into the same chart rows by date
    if bench_chart:
        bench_map = {row["date"]: row["benchmark"] for row in bench_chart}
        for row in equity_chart:
            row["benchmark"] = bench_map.get(row["date"])

    result: Dict[str, Any] = {
        "universe": list(prices.keys()),
        "signal_type": signal_type,
        "lookback_days": lookback_days,
        "spec": spec,
        "strategy_blueprint": sig.describe_spec(spec),
        "exposure": round(exposure, 3),
        "params": {
            "entry_threshold": entry_threshold,
            "exit_threshold": exit_threshold,
            "txn_cost_bps": settings.TXN_COST_BPS,
            "slippage_bps": settings.SLIPPAGE_BPS,
        },
        "metrics": metrics_full,
        "metrics_is": metrics_is,
        "metrics_oos": metrics_oos,
        "gross_cagr": gross_metrics.get("cagr", 0.0),
        "benchmark": bench_stats,
        "equity_curve": equity_chart,
    }

    if not deep:
        return result

    # --- Robustness suite ---
    sweep = _parameter_sweep(prices, spec, cost_per_turn)
    result["sensitivity"] = sweep["heatmap"]

    dsr = rb.deflated_sharpe_ratio(net, n_trials=max(2, sweep["n_configs"]), sr_trials=sweep["sr_trials"])
    pbo = rb.probability_of_backtest_overfitting(sweep["returns_matrix"])
    perm = rb.monte_carlo_permutation_test(signals_df, asset_ret_df, n=300)

    honesty = rb.honesty_score(
        is_sharpe=metrics_is.get("sharpe_ratio", 0.0),
        oos_sharpe=metrics_oos.get("sharpe_ratio", 0.0),
        dsr=dsr["dsr"],
        pbo=pbo["pbo"],
        permutation_p=perm["p_value"],
        gross_cagr=gross_metrics.get("cagr", 0.0),
        net_cagr=metrics_full.get("cagr", 0.0),
        beats_benchmark=bench_stats.get("beats_benchmark", False),
        information_ratio=bench_stats.get("information_ratio", 0.0),
        sensitivity_cv=sweep["cv"],
    )

    result["robustness"] = {
        "deflated_sharpe": dsr,
        "pbo": pbo,
        "permutation": perm,
    }
    result["honesty"] = honesty
    return result


# --------------------------------------------------------------------------- #
# Parameter sweep → heatmap + returns matrix for PBO + Sharpe trials for DSR
# --------------------------------------------------------------------------- #
def _parameter_sweep(prices, spec: Dict[str, Any], cost_per_turn: float) -> Dict[str, Any]:
    """
    Perturb the spec's numeric knobs (lookback windows + percent thresholds) and re-run, so
    PBO / deflated-Sharpe / sensitivity see the *whole neighbourhood* of the chosen config —
    the only honest way to tell a robust edge from a cherry-picked one. Works for any composed
    spec, not just the presets.
    """
    base_window = sig.primary_window(spec)
    base_thresh = sig.primary_threshold(spec)
    if sig.has_threshold_knob(spec):
        window_factors = (0.5, 0.75, 1.0, 1.5, 2.0)
        thresh_factors = (0.5, 1.0, 1.5, 2.0)
    else:
        # No percent threshold to vary — sweep windows more finely so configs stay distinct.
        window_factors = (0.5, 0.625, 0.75, 0.875, 1.0, 1.25, 1.5, 1.75, 2.0)
        thresh_factors = (1.0,)

    returns_cols: Dict[str, pd.Series] = {}
    heatmap: List[Dict[str, Any]] = []
    sr_trials: List[float] = []

    for wf in window_factors:
        for tf in thresh_factors:
            scaled = sig.scale_spec(spec, wf, tf)
            _, net_c, _, _ = _portfolio_returns(prices, scaled, cost_per_turn)
            if net_c.empty:
                continue
            sr = compute_metrics(net_c).get("sharpe_ratio", 0.0)
            sr_trials.append(sr)
            lb = max(3, int(round(base_window * wf)))
            en = round(base_thresh * tf, 4)
            returns_cols[f"w{wf}_t{tf}"] = net_c.reset_index(drop=True)
            heatmap.append({"lookback": lb, "entry": en, "oos_sharpe": sr})

    returns_matrix = pd.DataFrame(returns_cols).dropna(how="all") if returns_cols else pd.DataFrame()
    cv = None
    if len(sr_trials) > 2:
        mean_sr = np.mean(sr_trials)
        cv = float(np.std(sr_trials) / (abs(mean_sr) + 1e-9))

    return {
        "heatmap": heatmap,
        "returns_matrix": returns_matrix,
        "sr_trials": sr_trials,
        "n_configs": max(2, len(sr_trials)),
        "cv": cv,
    }
