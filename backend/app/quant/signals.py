"""
Composable signal DSL.

Instead of three hard-coded archetypes, a strategy is a *spec*: a small set of indicator
rules combined with AND/OR logic for entry and exit. The agent composes these specs; the
honest backtester + robustness suite then judge them — so richer signals never escape the
overfitting checks.

SignalSpec = {
  "name": str,
  "entry_logic": "all" | "any",
  "entry_rules": [Rule, ...],
  "exit_logic":  "all" | "any",
  "exit_rules":  [Rule, ...],
}
Rule = {"indicator": str, "param": int, "op": str, "value": float}

`value` for percent-style indicators (price_vs_sma, price_vs_ema, roc, sma_ratio) is a
fraction (0.02 == 2%). RSI/z-score/%B compare against their natural units.
"""
from __future__ import annotations

import copy
import pandas as pd
import numpy as np
import ta
from typing import Dict, Any, List, Tuple

# Indicators whose `param` is a lookback window (scaled during the sweep).
WINDOW_INDICATORS = {
    "price_vs_sma", "price_vs_ema", "rsi", "roc", "zscore", "bollinger_pctb", "sma_ratio",
}
# Indicators whose `value` is a percent threshold (scaled during the sweep).
PCT_THRESHOLD_INDICATORS = {"price_vs_sma", "price_vs_ema", "roc", "sma_ratio"}

VALID_OPS = {">", "<", ">=", "<=", "cross_above", "cross_below"}
VALID_INDICATORS = WINDOW_INDICATORS | {"macd_hist"}

_IND_TXT = {
    "price_vs_sma": "Price vs {p}d SMA",
    "price_vs_ema": "Price vs {p}d EMA",
    "rsi": "RSI({p})",
    "macd_hist": "MACD histogram",
    "roc": "{p}d return",
    "zscore": "{p}d z-score",
    "bollinger_pctb": "Bollinger %B({p})",
    "sma_ratio": "{p}d/{p3}d SMA ratio",
}
_OP_TXT = {">": ">", "<": "<", ">=": "≥", "<=": "≤", "cross_above": "crosses ↑", "cross_below": "crosses ↓"}


# --------------------------------------------------------------------------- #
# Indicator computation
# --------------------------------------------------------------------------- #
def _sma(c: pd.Series, n: int) -> pd.Series:
    return c.rolling(int(n)).mean()


def _ema(c: pd.Series, n: int) -> pd.Series:
    return c.ewm(span=int(n), adjust=False).mean()


def indicator_series(df: pd.DataFrame, indicator: str, param: int) -> pd.Series:
    c = df["Close"].astype(float)
    p = max(2, int(param or 14))
    if indicator == "price_vs_sma":
        return c / _sma(c, p) - 1
    if indicator == "price_vs_ema":
        return c / _ema(c, p) - 1
    if indicator == "rsi":
        return ta.momentum.rsi(c, window=p)
    if indicator == "macd_hist":
        return ta.trend.macd_diff(c)
    if indicator == "roc":
        return c.pct_change(p)
    if indicator == "zscore":
        m, s = _sma(c, p), c.rolling(p).std()
        return (c - m) / (s + 1e-9)
    if indicator == "bollinger_pctb":
        m, s = _sma(c, p), c.rolling(p).std()
        upper, lower = m + 2 * s, m - 2 * s
        return (c - lower) / ((upper - lower) + 1e-9)
    if indicator == "sma_ratio":
        return _sma(c, p) / _sma(c, p * 3) - 1
    raise ValueError(f"unknown indicator: {indicator}")


def _apply_op(series: pd.Series, op: str, value: float) -> pd.Series:
    v = float(value)
    if op == ">":
        return series > v
    if op == "<":
        return series < v
    if op == ">=":
        return series >= v
    if op == "<=":
        return series <= v
    prev = series.shift(1)
    if op == "cross_above":
        return (prev <= v) & (series > v)
    if op == "cross_below":
        return (prev >= v) & (series < v)
    raise ValueError(f"unknown op: {op}")


def _combine(df: pd.DataFrame, rules: List[Dict[str, Any]], logic: str) -> pd.Series:
    if not rules:
        return pd.Series(False, index=df.index)
    cols = []
    for r in rules:
        s = indicator_series(df, r["indicator"], r.get("param", 14))
        cols.append(_apply_op(s, r["op"], r.get("value", 0.0)).fillna(False))
    mat = pd.concat(cols, axis=1)
    return mat.all(axis=1) if logic == "all" else mat.any(axis=1)


def evaluate_spec(df: pd.DataFrame, spec: Dict[str, Any]) -> Tuple[pd.Series, pd.Series]:
    """Return (entry, exit) boolean series for a validated spec."""
    spec = validate_spec(spec)
    entry = _combine(df, spec["entry_rules"], spec.get("entry_logic", "all"))
    exit_ = _combine(df, spec["exit_rules"], spec.get("exit_logic", "any"))
    return entry.fillna(False), exit_.fillna(False)


# --------------------------------------------------------------------------- #
# Validation (defensive — agent input may be malformed)
# --------------------------------------------------------------------------- #
def _clean_rule(r: Dict[str, Any]) -> Dict[str, Any]:
    ind = r.get("indicator")
    op = r.get("op")
    if ind not in VALID_INDICATORS or op not in VALID_OPS:
        raise ValueError(f"invalid rule: {r}")
    param = int(r.get("param") or 14)
    param = max(2, min(param, 400))
    return {"indicator": ind, "param": param, "op": op, "value": float(r.get("value", 0.0))}


def validate_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError("spec must be an object")
    entry = [_clean_rule(r) for r in (spec.get("entry_rules") or [])]
    exit_ = [_clean_rule(r) for r in (spec.get("exit_rules") or [])]
    if not entry:
        raise ValueError("spec needs at least one entry rule")
    if not exit_:
        # default exit: leave when the first entry condition reverses
        e0 = entry[0]
        flip = {">": "<", ">=": "<", "<": ">", "<=": ">", "cross_above": "cross_below", "cross_below": "cross_above"}
        exit_ = [{**e0, "op": flip.get(e0["op"], "<")}]
    return {
        "name": str(spec.get("name", "Composite Strategy"))[:80],
        "entry_logic": "any" if spec.get("entry_logic") == "any" else "all",
        "entry_rules": entry[:5],
        "exit_logic": "all" if spec.get("exit_logic") == "all" else "any",
        "exit_rules": exit_[:5],
    }


# --------------------------------------------------------------------------- #
# Presets (back-compat with the old 3 archetypes)
# --------------------------------------------------------------------------- #
def preset_spec(signal_type: str, lookback: int, entry: float, exit: float) -> Dict[str, Any]:
    lb = max(3, int(lookback or 20))
    en = float(entry if entry is not None else 0.02)
    ex = float(exit if exit is not None else -0.01)
    if signal_type == "mean_reversion":
        return {
            "name": "Mean Reversion",
            "entry_logic": "all",
            "entry_rules": [
                {"indicator": "price_vs_sma", "param": lb, "op": "<", "value": ex},
                {"indicator": "rsi", "param": 14, "op": "<", "value": 40},
            ],
            "exit_logic": "any",
            "exit_rules": [
                {"indicator": "price_vs_sma", "param": lb, "op": ">=", "value": 0.0},
                {"indicator": "rsi", "param": 14, "op": ">", "value": 60},
            ],
        }
    if signal_type == "trend_following":
        return {
            "name": "Trend Following",
            "entry_logic": "all",
            "entry_rules": [{"indicator": "sma_ratio", "param": lb, "op": ">", "value": en}],
            "exit_logic": "any",
            "exit_rules": [{"indicator": "sma_ratio", "param": lb, "op": "<", "value": 0.0}],
        }
    return {  # momentum (default)
        "name": "Momentum",
        "entry_logic": "all",
        "entry_rules": [
            {"indicator": "price_vs_sma", "param": lb, "op": ">", "value": en},
            {"indicator": "rsi", "param": 14, "op": ">", "value": 50},
            {"indicator": "rsi", "param": 14, "op": "<", "value": 80},
        ],
        "exit_logic": "any",
        "exit_rules": [
            {"indicator": "price_vs_sma", "param": lb, "op": "<", "value": ex},
            {"indicator": "rsi", "param": 14, "op": ">", "value": 80},
        ],
    }


# --------------------------------------------------------------------------- #
# Sweep helpers — perturb the spec's numeric knobs for PBO / sensitivity
# --------------------------------------------------------------------------- #
def primary_window(spec: Dict[str, Any]) -> int:
    for r in spec["entry_rules"]:
        if r["indicator"] in WINDOW_INDICATORS:
            return int(r["param"])
    return 20


def primary_threshold(spec: Dict[str, Any]) -> float:
    for r in spec["entry_rules"]:
        if r["indicator"] in PCT_THRESHOLD_INDICATORS:
            return float(r["value"]) or 0.02
    return 0.02


def has_threshold_knob(spec: Dict[str, Any]) -> bool:
    return any(r["indicator"] in PCT_THRESHOLD_INDICATORS for r in spec["entry_rules"])


def scale_spec(spec: Dict[str, Any], window_factor: float, threshold_factor: float) -> Dict[str, Any]:
    s = copy.deepcopy(spec)
    for grp in ("entry_rules", "exit_rules"):
        for r in s[grp]:
            if r["indicator"] in WINDOW_INDICATORS:
                r["param"] = max(3, int(round(r["param"] * window_factor)))
            if r["indicator"] in PCT_THRESHOLD_INDICATORS and r.get("value"):
                r["value"] = round(float(r["value"]) * threshold_factor, 5)
    return s


# --------------------------------------------------------------------------- #
# Human-readable description (UI + agent)
# --------------------------------------------------------------------------- #
def describe_rule(r: Dict[str, Any]) -> str:
    p = int(r.get("param", 14))
    ind = _IND_TXT.get(r["indicator"], r["indicator"]).format(p=p, p3=p * 3)
    if r["indicator"] in PCT_THRESHOLD_INDICATORS:
        vtxt = f"{float(r['value']) * 100:.1f}%"
    else:
        vtxt = f"{float(r['value']):g}"
    return f"{ind} {_OP_TXT.get(r['op'], r['op'])} {vtxt}"


def describe_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    spec = validate_spec(spec)
    return {
        "name": spec["name"],
        "entry_logic": spec["entry_logic"],
        "entry": [describe_rule(r) for r in spec["entry_rules"]],
        "exit_logic": spec["exit_logic"],
        "exit": [describe_rule(r) for r in spec["exit_rules"]],
    }
