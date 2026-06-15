"""
Agentic research runtime.

A single skeptical "quant PM" agent that is given tools (real quant engines) and must
*try to disprove* a strategy's edge before approving it. It streams its reasoning as a
sequence of events:

    agent_start → thought → tool_call → tool_result → ... → verdict → complete

The same event stream powers both the SSE endpoint (live UI) and the non-streaming
`/workflow` endpoint (collected into a log). When no OpenAI key is configured, a scripted
mock agent drives the *same real tools*, so the honesty verdict is genuine even offline.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterator, List, Tuple

from app.core.config import settings
from app.services.llm_service import LLMService
from app.services.market_data_service import MarketDataService
from app.services.drift_detection_service import DriftDetectionService
from app.quant.backtester import run_backtest
from app.quant.portfolio import optimize_portfolio
from app.quant import signals as sig_lib

import pandas as pd

MAX_STEPS = 7

SYSTEM_PROMPT = """You are a skeptical Senior Portfolio Manager at a quant hedge fund. Your job is \
NOT to make strategies look good — it is to find out whether an edge is REAL or just overfit noise, \
before any capital is risked.

Workflow you must follow:
1. Decide a universe (3-5 US tickers) and COMPOSE a signal via `signal_spec`: 1-4 entry rules and \
1-3 exit rules combined with "all"/"any" logic. Each rule is an indicator + operator + value, e.g. \
price_vs_sma > 0.02, rsi < 35, roc(10) > 0, macd_hist crosses_above 0, sma_ratio > 0, zscore < -1. \
Call `run_backtest`. It returns an HONEST backtest: out-of-sample metrics, trading costs, benchmark \
comparison, and a 0-100 honesty_score with a verdict (Robust / Fragile / Likely Overfit). \
(You may instead pass a simple signal_type preset, but composing rules is preferred.)
2. Read the honesty verdict critically. If it is "Likely Overfit", try ONE structurally different \
composition (different indicators/logic or universe) with another `run_backtest`. A simpler spec that \
holds out-of-sample beats a complex one that doesn't. Do not endlessly fish for a good result.
3. Call `check_regime_drift` to confirm current market conditions resemble the backtest regime.
4. If the best strategy is at least "Fragile" and passes risk, call `optimize_portfolio`.
5. Call `finalize` with your recommendation ("approve" or "reject"), the chosen honesty score, and a \
two-sentence verdict that is honest about the strategy's weaknesses.

Be concise. Prefer rejecting an overfit strategy over approving a flattering backtest."""


# --------------------------------------------------------------------------- #
# Tool schemas (OpenAI function-calling format)
# --------------------------------------------------------------------------- #
_RULE_SCHEMA = {
    "type": "object",
    "properties": {
        "indicator": {
            "type": "string",
            "enum": ["price_vs_sma", "price_vs_ema", "rsi", "macd_hist", "roc",
                     "zscore", "bollinger_pctb", "sma_ratio"],
        },
        "param": {"type": "integer", "description": "lookback window (e.g. 14, 20, 50)"},
        "op": {"type": "string", "enum": [">", "<", ">=", "<=", "cross_above", "cross_below"]},
        "value": {"type": "number", "description": "threshold; percent indicators use fractions (0.02 = 2%)"},
    },
    "required": ["indicator", "op", "value"],
}

TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "run_backtest",
            "description": "Run an honest backtest with costs, out-of-sample split, benchmark and a full robustness/overfitting suite. Returns metrics + honesty_score. Compose a signal via signal_spec (preferred) or use a signal_type preset.",
            "parameters": {
                "type": "object",
                "properties": {
                    "universe": {"type": "array", "items": {"type": "string"}, "description": "3-5 US equity tickers"},
                    "signal_type": {"type": "string", "enum": ["momentum", "mean_reversion", "trend_following"],
                                    "description": "Preset, used only when signal_spec is omitted"},
                    "lookback_days": {"type": "integer"},
                    "entry_threshold": {"type": "number"},
                    "exit_threshold": {"type": "number"},
                    "signal_spec": {
                        "type": "object",
                        "description": "Composable signal. Overrides signal_type when provided.",
                        "properties": {
                            "name": {"type": "string"},
                            "entry_logic": {"type": "string", "enum": ["all", "any"]},
                            "exit_logic": {"type": "string", "enum": ["all", "any"]},
                            "entry_rules": {"type": "array", "items": _RULE_SCHEMA},
                            "exit_rules": {"type": "array", "items": _RULE_SCHEMA},
                        },
                        "required": ["entry_rules"],
                    },
                },
                "required": ["universe"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_regime_drift",
            "description": "Compare the recent market regime against the longer-run history (KS test + PSI) to see if conditions have shifted away from the backtest regime.",
            "parameters": {
                "type": "object",
                "properties": {"universe": {"type": "array", "items": {"type": "string"}}},
                "required": ["universe"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_portfolio",
            "description": "Compute risk-aware portfolio weights via Hierarchical Risk Parity (HRP).",
            "parameters": {
                "type": "object",
                "properties": {
                    "universe": {"type": "array", "items": {"type": "string"}},
                    "method": {"type": "string", "enum": ["hrp", "mean_variance"]},
                },
                "required": ["universe"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finalize",
            "description": "End the research with a recommendation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recommendation": {"type": "string", "enum": ["approve", "reject"]},
                    "honesty_score": {"type": "number"},
                    "verdict": {"type": "string", "description": "Two-sentence honest summary"},
                },
                "required": ["recommendation", "verdict"],
            },
        },
    },
]


# --------------------------------------------------------------------------- #
# Tool dispatch — calls the REAL engines. Returns (llm_summary, ui_payload).
# `state` accumulates full results for the final assembled output.
# --------------------------------------------------------------------------- #
def _dispatch(name: str, args: Dict[str, Any], state: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if name == "run_backtest":
        universe = args.get("universe") or ["AAPL", "MSFT", "GOOGL"]
        full = run_backtest(
            universe=universe,
            signal_type=args.get("signal_type", "momentum"),
            lookback_days=int(args.get("lookback_days", 20) or 20),
            entry_threshold=float(args.get("entry_threshold", 0.02) or 0.02),
            exit_threshold=float(args.get("exit_threshold", -0.01) or -0.01),
            signal_spec=args.get("signal_spec"),
        )
        if "error" in full:
            return {"error": full["error"]}, {"error": full["error"]}
        full["strategy_params"] = {
            "universe": universe,
            "signal_type": full.get("signal_type", "momentum"),
            "spec": full.get("spec"),
            "blueprint": full.get("strategy_blueprint"),
        }
        state.setdefault("backtests", []).append(full)
        honesty = full.get("honesty", {})
        summary = {
            "honesty_score": honesty.get("score"),
            "verdict": honesty.get("verdict"),
            "reasons": honesty.get("reasons", [])[:3],
            "strategy": full.get("strategy_blueprint", {}).get("name"),
            "exposure": full.get("exposure"),
            "oos_sharpe": full.get("metrics_oos", {}).get("sharpe_ratio"),
            "is_sharpe": full.get("metrics_is", {}).get("sharpe_ratio"),
            "net_cagr": full.get("metrics", {}).get("cagr"),
            "beats_benchmark": full.get("benchmark", {}).get("beats_benchmark"),
            "cvar_95": full.get("metrics", {}).get("cvar_95"),
        }
        return summary, full

    if name == "check_regime_drift":
        universe = args.get("universe") or ["SPY"]
        drift = _regime_drift(universe)
        state["drift"] = drift
        return drift, drift

    if name == "optimize_portfolio":
        universe = args.get("universe") or ["AAPL", "MSFT", "GOOGL"]
        opt = optimize_portfolio(universe, method=args.get("method", "hrp"))
        state["portfolio"] = opt
        return opt, opt

    if name == "finalize":
        state["final"] = args
        return args, args

    return {"error": f"unknown tool {name}"}, {"error": f"unknown tool {name}"}


def _regime_drift(universe: List[str]) -> Dict[str, Any]:
    """Compare recent 60d returns vs the prior ~1y for the universe — ties the drift engine in."""
    series: List[float] = []
    ref: List[float] = []
    for ticker in (universe or ["SPY"])[:5]:
        raw = MarketDataService.fetch_historical_data(ticker, period="2y", interval="1d")
        if "error" in raw or not raw.get("data"):
            continue
        df = pd.DataFrame(raw["data"])
        if "Close" not in df.columns:
            continue
        rets = df["Close"].astype(float).pct_change().dropna().values
        if len(rets) < 120:
            continue
        ref.extend(rets[:-60].tolist())
        series.extend(rets[-60:].tolist())
    if len(series) < 30 or len(ref) < 30:
        return {"available": False, "note": "insufficient history for regime check"}
    res = DriftDetectionService.detect_drift_statistical(ref, series)
    psi = res["psi"]["value"]
    severity = "high" if psi >= 0.2 else "medium" if psi >= 0.1 else "low"
    return {
        "available": True,
        "psi": round(psi, 4),
        "ks_p_value": round(res["ks_test"]["p_value"], 4),
        "regime_shift": res["overall_drift"],
        "severity": severity,
    }


# --------------------------------------------------------------------------- #
# Live agent loop
# --------------------------------------------------------------------------- #
def _live_stream(user_request: str, state: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_request},
    ]
    for _ in range(MAX_STEPS):
        turn = LLMService.agent_turn(messages, TOOL_SCHEMAS)
        if turn is None:
            yield from _mock_stream(user_request, state)
            return
        if turn["content"]:
            yield {"type": "thought", "text": turn["content"]}
        if not turn["tool_calls"]:
            yield from _emit_verdict(state, fallback_text=turn["content"])
            return

        messages.append({
            "role": "assistant",
            "content": turn["content"] or None,
            "tool_calls": [
                {"id": tc["id"], "type": "function",
                 "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])}}
                for tc in turn["tool_calls"]
            ],
        })
        for tc in turn["tool_calls"]:
            yield {"type": "tool_call", "tool": tc["name"], "args": tc["arguments"]}
            summary, ui = _dispatch(tc["name"], tc["arguments"], state)
            yield {"type": "tool_result", "tool": tc["name"], "summary": summary, "data": ui}
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(summary)})
            if tc["name"] == "finalize":
                yield from _emit_verdict(state)
                return
    yield from _emit_verdict(state)


# --------------------------------------------------------------------------- #
# Mock agent — scripted, but drives the same REAL tools (works fully offline)
# --------------------------------------------------------------------------- #
_KNOWN_TICKERS = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "AMZN", "META", "AMD", "SPY", "JPM", "NFLX"]


def _compose_spec(signal: str) -> Dict[str, Any]:
    """Build a multi-rule composed signal for the chosen style (used by the offline mock)."""
    if signal == "mean_reversion":
        return {
            "name": "Mean Reversion + RSI + z-score",
            "entry_logic": "all",
            "entry_rules": [
                {"indicator": "zscore", "param": 20, "op": "<", "value": -1.0},
                {"indicator": "rsi", "param": 14, "op": "<", "value": 35},
            ],
            "exit_logic": "any",
            "exit_rules": [
                {"indicator": "zscore", "param": 20, "op": ">=", "value": 0.0},
                {"indicator": "rsi", "param": 14, "op": ">", "value": 55},
            ],
        }
    if signal == "trend_following":
        return {
            "name": "Trend: SMA cross + MACD confirm",
            "entry_logic": "all",
            "entry_rules": [
                {"indicator": "sma_ratio", "param": 20, "op": "cross_above", "value": 0.0},
                {"indicator": "macd_hist", "param": 0, "op": ">", "value": 0.0},
            ],
            "exit_logic": "any",
            "exit_rules": [{"indicator": "sma_ratio", "param": 20, "op": "<", "value": -0.01}],
        }
    return {
        "name": "Momentum + RSI filter + MACD",
        "entry_logic": "all",
        "entry_rules": [
            {"indicator": "price_vs_sma", "param": 20, "op": ">", "value": 0.02},
            {"indicator": "rsi", "param": 14, "op": ">", "value": 50},
            {"indicator": "macd_hist", "param": 0, "op": ">", "value": 0.0},
        ],
        "exit_logic": "any",
        "exit_rules": [
            {"indicator": "price_vs_sma", "param": 20, "op": "<", "value": -0.01},
            {"indicator": "rsi", "param": 14, "op": ">", "value": 80},
        ],
    }


def _infer_params(user_request: str) -> Dict[str, Any]:
    text = user_request.upper()
    universe = [t for t in _KNOWN_TICKERS if re.search(rf"\b{t}\b", text)]
    if not universe:
        universe = ["AAPL", "MSFT", "NVDA"]
    low = user_request.lower()
    if "mean revers" in low or "reversion" in low or "oversold" in low:
        signal = "mean_reversion"
    elif "trend" in low or "breakout" in low or "cross" in low:
        signal = "trend_following"
    else:
        signal = "momentum"
    return {"universe": universe[:5], "signal_type": signal, "signal_spec": _compose_spec(signal)}


def _mock_stream(user_request: str, state: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    params = _infer_params(user_request)
    rules = params["signal_spec"]["entry_rules"]
    rule_txt = ", ".join(sig_lib.describe_rule(r) for r in rules)
    yield {"type": "thought", "text": f"Composing a {params['signal_type'].replace('_', ' ')} signal on {', '.join(params['universe'])} — entry when {rule_txt}. Running an honest, cost-aware backtest with an out-of-sample split before I believe anything."}

    yield {"type": "tool_call", "tool": "run_backtest", "args": params}
    summary, full = _dispatch("run_backtest", params, state)
    yield {"type": "tool_result", "tool": "run_backtest", "summary": summary, "data": full}

    verdict = summary.get("verdict")
    yield {"type": "thought", "text": f"Honesty score {summary.get('honesty_score')} → {verdict}. Out-of-sample Sharpe {summary.get('oos_sharpe')} vs in-sample {summary.get('is_sharpe')} (exposure {summary.get('exposure')})."}

    if verdict == "Likely Overfit":
        alt_signal = "mean_reversion" if params["signal_type"] != "mean_reversion" else "trend_following"
        alt = {"universe": params["universe"], "signal_type": alt_signal, "signal_spec": _compose_spec(alt_signal)}
        yield {"type": "thought", "text": f"That edge looks like fitted noise. Before rejecting, I'll test a structurally different composition: a {alt_signal.replace('_', ' ')} rule set."}
        yield {"type": "tool_call", "tool": "run_backtest", "args": alt}
        summary2, full2 = _dispatch("run_backtest", alt, state)
        yield {"type": "tool_result", "tool": "run_backtest", "summary": summary2, "data": full2}

    yield {"type": "tool_call", "tool": "check_regime_drift", "args": {"universe": params["universe"]}}
    d_sum, d_ui = _dispatch("check_regime_drift", {"universe": params["universe"]}, state)
    yield {"type": "tool_result", "tool": "check_regime_drift", "summary": d_sum, "data": d_ui}

    best = _best_backtest(state)
    best_score = best.get("honesty", {}).get("score", 0) if best else 0
    if best_score >= 40:
        yield {"type": "thought", "text": "At least marginally robust and within risk limits — sizing it with hierarchical risk parity."}
        yield {"type": "tool_call", "tool": "optimize_portfolio", "args": {"universe": best["strategy_params"]["universe"], "method": "hrp"}}
        p_sum, p_ui = _dispatch("optimize_portfolio", {"universe": best["strategy_params"]["universe"], "method": "hrp"}, state)
        yield {"type": "tool_result", "tool": "optimize_portfolio", "summary": p_sum, "data": p_ui}

    yield from _emit_verdict(state)


# --------------------------------------------------------------------------- #
# Final assembly
# --------------------------------------------------------------------------- #
def _best_backtest(state: Dict[str, Any]) -> Dict[str, Any]:
    bts = state.get("backtests", [])
    if not bts:
        return {}
    return max(bts, key=lambda b: b.get("honesty", {}).get("score", 0))


def _emit_verdict(state: Dict[str, Any], fallback_text: str = "") -> Iterator[Dict[str, Any]]:
    best = _best_backtest(state)
    honesty = best.get("honesty", {}) if best else {}
    score = honesty.get("score", 0)
    verdict = honesty.get("verdict", "Unknown")

    metrics = best.get("metrics", {}) if best else {}
    cvar = abs(metrics.get("cvar_95", 0.0) or 0.0)
    risk_ok = cvar <= settings.RISK_CVAR_LIMIT

    final = state.get("final", {})
    recommendation = final.get("recommendation")
    if recommendation not in ("approve", "reject"):
        recommendation = "approve" if (score >= 40 and risk_ok) else "reject"

    text = final.get("verdict") or fallback_text or (
        f"{verdict} ({score}/100). " + (
            "Edge survives out-of-sample testing, costs and overfitting checks." if recommendation == "approve"
            else "The apparent edge does not survive honest out-of-sample and overfitting scrutiny."
        )
    )

    yield {
        "type": "verdict",
        "recommendation": recommendation,
        "honesty": honesty,
        "risk_ok": risk_ok,
        "text": text,
    }
    yield {"type": "complete", "result": assemble_result(state, recommendation, text)}


def assemble_result(state: Dict[str, Any], recommendation: str, verdict_text: str) -> Dict[str, Any]:
    best = _best_backtest(state)
    honesty = best.get("honesty", {}) if best else {}
    params = best.get("strategy_params", {}) if best else {}
    return {
        "status": "completed",
        "recommendation": recommendation,
        "verdict_text": verdict_text,
        "strategy": params,
        "backtest": best,
        "portfolio": state.get("portfolio", {}),
        "drift": state.get("drift", {}),
        "honesty": honesty,
    }


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #
def research_stream(user_request: str) -> Iterator[Dict[str, Any]]:
    state: Dict[str, Any] = {}
    yield {"type": "agent_start", "live": LLMService.is_live()}
    if LLMService.is_live():
        yield from _live_stream(user_request, state)
    else:
        yield from _mock_stream(user_request, state)


def research_blocking(user_request: str) -> Dict[str, Any]:
    """Run the full research and return the final result plus the event log (no streaming)."""
    events: List[Dict[str, Any]] = []
    result: Dict[str, Any] = {"status": "completed"}
    for ev in research_stream(user_request):
        events.append(ev)
        if ev["type"] == "complete":
            result = ev["result"]
    result["events"] = events
    return result
