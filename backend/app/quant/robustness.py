"""
Robustness / anti-overfitting statistics — the engine behind Quantora's "Honesty Score".

Everything here is pure numpy/scipy/pandas (no extra deps). These routines answer the
single question that destroys most quant strategies: *is the backtest edge real, or did we
just fit noise?*

References:
  - Bailey & López de Prado, "The Deflated Sharpe Ratio" (2014)
  - Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting" (2015)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from itertools import combinations
from math import comb
from scipy.stats import norm
from typing import Dict, Any, List, Optional

EULER_MASCHERONI = 0.5772156649015329
ANN = 252


# --------------------------------------------------------------------------- #
# Sharpe helpers
# --------------------------------------------------------------------------- #
def _per_period_sharpe(returns: np.ndarray) -> float:
    """Non-annualised Sharpe (per observation). Used by the DSR statistic."""
    sd = returns.std(ddof=1)
    if sd < 1e-12:
        return 0.0
    return float(returns.mean() / sd)


def annualised_sharpe(returns: pd.Series, rf: float = 0.04) -> float:
    r = returns.dropna().values
    if len(r) < 2 or r.std() < 1e-12:
        return 0.0
    return float((r.mean() * ANN - rf) / (r.std(ddof=1) * np.sqrt(ANN)))


# --------------------------------------------------------------------------- #
# Probabilistic & Deflated Sharpe Ratio
# --------------------------------------------------------------------------- #
def probabilistic_sharpe_ratio(returns: pd.Series, sr_benchmark: float = 0.0) -> float:
    """
    Probability that the *true* (per-period) Sharpe exceeds `sr_benchmark`, correcting
    for sample length, skew and kurtosis. Returns a probability in [0, 1].
    """
    r = returns.dropna().values
    n = len(r)
    if n < 8:
        return 0.0
    sr = _per_period_sharpe(r)
    skew = float(pd.Series(r).skew())
    kurt = float(pd.Series(r).kurtosis()) + 3.0  # pandas gives excess kurtosis
    denom = np.sqrt(max(1e-12, 1 - skew * sr + ((kurt - 1) / 4.0) * sr ** 2))
    psr = norm.cdf(((sr - sr_benchmark) * np.sqrt(n - 1)) / denom)
    return float(np.clip(psr, 0.0, 1.0))


def expected_max_sharpe(sr_std: float, n_trials: int) -> float:
    """Expected maximum per-period Sharpe across `n_trials` independent strategies."""
    n_trials = max(2, int(n_trials))
    z1 = norm.ppf(1 - 1.0 / n_trials)
    z2 = norm.ppf(1 - 1.0 / (n_trials * np.e))
    return float(sr_std * ((1 - EULER_MASCHERONI) * z1 + EULER_MASCHERONI * z2))


def deflated_sharpe_ratio(
    returns: pd.Series,
    n_trials: int,
    sr_trials: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Deflated Sharpe Ratio: the PSR evaluated against the Sharpe we'd *expect to see by
    chance* given how many strategy variants were tried. A DSR near 1.0 means the edge
    survives multiple-testing deflation; near 0.0 means it's likely a fluke.
    """
    r = returns.dropna().values
    n = len(r)
    if n < 8:
        return {"dsr": 0.0, "expected_max_sharpe_ann": 0.0, "n_trials": n_trials}

    # Variance of the Sharpe estimate across trials: use observed spread if we have it,
    # otherwise fall back to the analytic approximation Var(SR) ~ (1 + SR^2/2) / T.
    if sr_trials and len(sr_trials) > 2:
        sr_std = float(np.std(sr_trials, ddof=1)) / np.sqrt(ANN)  # de-annualise
    else:
        sr = _per_period_sharpe(r)
        sr_std = np.sqrt((1 + 0.5 * sr ** 2) / n)

    sr0 = expected_max_sharpe(sr_std, n_trials)
    dsr = probabilistic_sharpe_ratio(returns, sr_benchmark=sr0)
    return {
        "dsr": round(float(dsr), 4),
        "expected_max_sharpe_ann": round(float(sr0 * np.sqrt(ANN)), 3),
        "n_trials": int(n_trials),
    }


# --------------------------------------------------------------------------- #
# Probability of Backtest Overfitting (CSCV)
# --------------------------------------------------------------------------- #
def probability_of_backtest_overfitting(returns_matrix: pd.DataFrame, n_splits: int = 8) -> Dict[str, Any]:
    """
    Combinatorially Symmetric Cross-Validation (CSCV).

    `returns_matrix`: columns = strategy configurations, rows = time. We repeatedly split
    time into IS/OOS halves, pick the best config in-sample, then look at its rank
    out-of-sample. PBO = probability the in-sample winner lands below the OOS median —
    i.e. the share of the time our "best" config is really just overfit.
    """
    m = returns_matrix.dropna()
    n_configs = m.shape[1]
    if n_configs < 2 or m.shape[0] < n_splits * 2:
        return {"pbo": 0.0, "n_configs": int(n_configs), "note": "insufficient configs/history"}

    n_splits = n_splits if n_splits % 2 == 0 else n_splits + 1
    rows = np.array_split(np.arange(m.shape[0]), n_splits)

    def sharpe_cols(block: np.ndarray) -> np.ndarray:
        sub = m.values[block]
        mu = sub.mean(axis=0)
        sd = sub.std(axis=0, ddof=1)
        sd[sd < 1e-12] = 1e-12
        return mu / sd

    logits: List[float] = []
    half = n_splits // 2
    for is_idx in combinations(range(n_splits), half):
        is_blocks = np.concatenate([rows[i] for i in is_idx])
        oos_blocks = np.concatenate([rows[i] for i in range(n_splits) if i not in is_idx])
        is_sr = sharpe_cols(is_blocks)
        oos_sr = sharpe_cols(oos_blocks)
        best = int(np.argmax(is_sr))
        # relative rank of the IS winner in the OOS Sharpe distribution
        rank = (np.sum(oos_sr <= oos_sr[best])) / n_configs
        rank = min(max(rank, 1e-6), 1 - 1e-6)
        logits.append(np.log(rank / (1 - rank)))

    logits_arr = np.array(logits)
    pbo = float(np.mean(logits_arr <= 0))
    return {
        "pbo": round(pbo, 4),
        "n_configs": int(n_configs),
        "n_combinations": int(comb(n_splits, half)),
    }


# --------------------------------------------------------------------------- #
# Monte-Carlo permutation test (skill vs luck)
# --------------------------------------------------------------------------- #
def monte_carlo_permutation_test(
    signals: pd.DataFrame,
    asset_returns: pd.DataFrame,
    n: int = 500,
    seed: int = 7,
) -> Dict[str, Any]:
    """
    Tests whether the *timing* in our signals carries information. We circularly shift
    each asset's signal by a random lag (breaking the signal↔return alignment while
    preserving each series' autocorrelation), rebuild the equal-weight portfolio, and
    recompute Sharpe. p-value = share of random shifts that beat the real strategy.
    A low p-value means the edge is real; high means it's indistinguishable from luck.
    """
    rng = np.random.default_rng(seed)
    sig = signals.fillna(0.0)
    ret = asset_returns.fillna(0.0)
    cols = [c for c in sig.columns if c in ret.columns]
    if not cols or len(sig) < 30:
        return {"p_value": 1.0, "n": 0, "actual_sharpe": 0.0, "note": "insufficient data"}

    sig_v = sig[cols].values
    ret_v = ret[cols].values
    T = sig_v.shape[0]

    def portfolio_sharpe(s: np.ndarray) -> float:
        port = (s * ret_v).mean(axis=1)
        sd = port.std(ddof=1)
        return 0.0 if sd < 1e-12 else float(port.mean() / sd * np.sqrt(ANN))

    actual = portfolio_sharpe(sig_v)
    wins = 0
    for _ in range(n):
        shifted = np.empty_like(sig_v)
        for j in range(sig_v.shape[1]):
            shifted[:, j] = np.roll(sig_v[:, j], int(rng.integers(1, T)))
        if portfolio_sharpe(shifted) >= actual:
            wins += 1
    p = (wins + 1) / (n + 1)  # add-one smoothing
    return {
        "p_value": round(float(p), 4),
        "n": int(n),
        "actual_sharpe": round(float(actual), 3),
        "skill_detected": bool(p < 0.05),
    }


# --------------------------------------------------------------------------- #
# Honesty Score — the headline artifact
# --------------------------------------------------------------------------- #
def honesty_score(
    *,
    is_sharpe: float,
    oos_sharpe: float,
    dsr: float,
    pbo: float,
    permutation_p: float,
    gross_cagr: float,
    net_cagr: float,
    beats_benchmark: bool,
    information_ratio: float,
    sensitivity_cv: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Fold the robustness diagnostics into a single 0–100 score + verdict + plain-English
    reasons. Higher = more trustworthy. This is deliberately opinionated and skeptical.
    """
    reasons: List[str] = []

    # 1. OOS decay (25 pts): how much of in-sample Sharpe survives out-of-sample.
    if is_sharpe <= 0:
        decay = 0.0
    else:
        decay = float(np.clip(oos_sharpe / is_sharpe, 0.0, 1.0))
    s_decay = 25 * decay
    if decay < 0.4:
        reasons.append(f"Out-of-sample Sharpe collapses to {decay*100:.0f}% of in-sample — classic overfit signature.")
    elif decay > 0.7:
        reasons.append(f"Edge holds out-of-sample ({decay*100:.0f}% of in-sample Sharpe retained).")

    # 2. Deflated Sharpe (25 pts): survives multiple-testing deflation.
    s_dsr = 25 * float(np.clip(dsr, 0.0, 1.0))
    if dsr < 0.5:
        reasons.append(f"Deflated Sharpe Ratio is only {dsr:.2f} — Sharpe is not significant after accounting for the configs tried.")
    elif dsr > 0.9:
        reasons.append(f"Deflated Sharpe Ratio {dsr:.2f}: edge survives multiple-testing deflation.")

    # 3. PBO (20 pts): probability the config is overfit (lower is better).
    s_pbo = 20 * float(np.clip(1.0 - pbo, 0.0, 1.0))
    if pbo > 0.5:
        reasons.append(f"Probability of Backtest Overfitting is {pbo*100:.0f}% — the chosen parameters are likely cherry-picked.")
    elif pbo < 0.2:
        reasons.append(f"Low overfitting probability ({pbo*100:.0f}%): parameter choice is stable across splits.")

    # 4. Permutation / skill (15 pts): low p-value = real timing skill.
    s_perm = 15 * float(np.clip(1.0 - permutation_p / 0.5, 0.0, 1.0))
    if permutation_p > 0.2:
        reasons.append(f"Permutation test p={permutation_p:.2f}: returns are statistically indistinguishable from random timing.")
    elif permutation_p < 0.05:
        reasons.append(f"Permutation test p={permutation_p:.2f}: timing carries genuine information.")

    # 5. Costs + benchmark (15 pts): does it survive trading frictions and beat buy-and-hold?
    cost_drag = gross_cagr - net_cagr
    survives_costs = net_cagr > 0
    s_costs = 7.5 if survives_costs else 0.0
    s_bench = 7.5 if beats_benchmark else 0.0
    if not survives_costs and gross_cagr > 0:
        reasons.append(f"Profitable gross (+{gross_cagr*100:.1f}%) but trading costs ({cost_drag*100:.1f}%) push net CAGR to {net_cagr*100:.1f}%.")
    if not beats_benchmark:
        reasons.append("Does not beat a simple buy-and-hold of the benchmark on a risk-adjusted basis.")
    elif information_ratio > 0.5:
        reasons.append(f"Beats benchmark with information ratio {information_ratio:.2f}.")

    # 6. Parameter sensitivity (bonus/penalty up to ±5): flat surface good, spiky bad.
    s_sens = 0.0
    if sensitivity_cv is not None:
        # coefficient of variation of OOS Sharpe across the grid; high = fragile
        s_sens = 5 * float(np.clip(1.0 - sensitivity_cv, -1.0, 1.0))
        if sensitivity_cv > 0.8:
            reasons.append("Performance is highly sensitive to parameter choice (fragile surface).")

    score = s_decay + s_dsr + s_pbo + s_perm + s_costs + s_bench + s_sens
    score = float(np.clip(score, 0.0, 100.0))

    if score >= 65:
        verdict = "Robust"
    elif score >= 40:
        verdict = "Fragile"
    else:
        verdict = "Likely Overfit"

    return {
        "score": round(score, 1),
        "verdict": verdict,
        "reasons": reasons,
        "components": {
            "oos_decay": round(decay, 3),
            "deflated_sharpe": round(float(dsr), 3),
            "pbo": round(float(pbo), 3),
            "permutation_p": round(float(permutation_p), 3),
            "net_cagr": round(float(net_cagr), 4),
            "cost_drag": round(float(cost_drag), 4),
            "beats_benchmark": bool(beats_benchmark),
            "information_ratio": round(float(information_ratio), 3),
        },
    }
