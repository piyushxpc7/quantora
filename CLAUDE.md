# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (Python / FastAPI)
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload          # runs on http://localhost:8000
```

API docs at `http://localhost:8000/docs`. On first boot, SQLAlchemy auto-creates all tables.

Seed sample data (requires DB running):
```bash
cd backend && python3 -m scripts.seed
```

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev      # runs on http://localhost:3000
npx tsc --noEmit # type check
npm run lint
```

### Docker (full stack including TimescaleDB)
```bash
cp .env.example .env   # fill in OPENAI_API_KEY
docker-compose up --build
```

Backend: port 8000 · Frontend: port 3000 · TimescaleDB: port 5432

## Architecture

Quantora is a multi-agent quantitative finance platform. FastAPI backend, Next.js frontend, TimescaleDB for persistence.

### Backend (`backend/`)
- `main.py` — FastAPI entry point; CORS middleware; lifespan hook runs `create_tables()` then `dispose_engine()`
- `app/core/config.py` — `Settings` (pydantic-settings): `OPENAI_API_KEY`, `OPENAI_MODEL`, `DATABASE_URL`, `BACKEND_CORS_ORIGINS`, `RISK_CVAR_LIMIT`
- `app/core/database.py` — async SQLAlchemy engine + `AsyncSessionLocal`; `get_db()` dependency; `create_tables()` / `dispose_engine()`
- `app/api/v1/api.py` — mounts four routers: `market-data`, `drift`, `agents`, `stream`

**Services** (`app/services/`):
- `market_data_service.py` — real yfinance OHLCV + latest price
- `feature_engineering_service.py` — `add_technical_indicators` (SMA, EMA, RSI, MACD, Bollinger via `ta`)
- `drift_detection_service.py` — real PSI, KS-test, PyTorch autoencoder; the platform's star engine
- `llm_service.py` — OpenAI `gpt-4o` with JSON mode; **graceful fallback to keyword mock if `OPENAI_API_KEY` is unset** — demo never crashes offline

**Quant engines** (`app/quant/`):
- `backtester.py` — vectorized backtester; fetches yfinance OHLCV, applies technical indicators, generates signals (momentum / mean_reversion / trend_following), computes equity curve
- `metrics.py` — `compute_metrics(returns)`: CAGR, Sharpe, Sortino, max drawdown, VaR(95%), CVaR(95%)
- `portfolio.py` — `optimize_portfolio(universe)`: HRP or Mean-Variance via `PyPortfolioOpt`; falls back to equal-weight if library unavailable

**Agent pipeline** (`app/agents/`):
1. `StrategyAgent` — LLM generates structured JSON params (universe, signal_type, lookback, thresholds)
2. `BacktestAgent` — runs real `backtester.run_backtest()` using strategy params; LLM adds narrative
3. `RiskAgent` — computes real VaR/CVaR from backtest metrics; compares against `RISK_CVAR_LIMIT`; sets `risk_approved` (real gate, not always-True)
4. `PortfolioAgent` — runs real HRP optimizer; returns actual weights
- `manager.py` — orchestrates Strategy→Backtest→Risk→Portfolio; halts if `risk_approved=False`

**Persistence** (`app/models/`, `app/repositories/`):
- `WorkflowRun` — every agent pipeline run, including metrics and full `workflow_log` JSON
- `DriftReport` — PSI, KS stats, severity per drift analysis
- `workflow_repo.py` / `drift_repo.py` — async CRUD; dashboard stats aggregated here

**Endpoints** (`app/api/v1/endpoints/`):
- `agents.py` — `POST /workflow`, `GET /runs`, `GET /stats`
- `drift.py` — `POST /analyze`, `GET /history`, `GET /summary`, `POST /train-model`, `POST /detect-anomalies`
- `market_data.py` — `GET /historical/{ticker}`, `GET /price/{ticker}`
- `stream.py` — `WS /stream/prices` — pushes live prices for AAPL/MSFT/GOOGL/NVDA/TSLA every 15s

### Frontend (`frontend/`)
- Next.js 16 App Router; Tailwind CSS v4; Recharts for charts
- `lib/api.ts` — typed fetch wrapper using `NEXT_PUBLIC_API_URL`; all pages call real backend endpoints
- `app/page.tsx` — Dashboard: live stats from `/agents/stats`, equity curve from latest run's `workflow_log`
- `app/agents/page.tsx` — Chat UI wired to real `POST /agents/workflow`; renders per-agent step cards with metrics, equity curve, and allocation
- `app/drift/page.tsx` — Drift monitor: live PSI/KS from `/drift/summary` + `/drift/history`; "Run Drift Check" button calls `/drift/analyze`
- `app/settings/page.tsx` — Platform config info page
- `components/DriftChart.tsx` — Recharts LineChart accepting `data` prop (real history); fallback to demo data when empty
- `components/Sidebar.tsx` — Nav with links to Dashboard, AI Agents, Drift Monitor, Settings

### Shared
- `shared/utils.py` — common utilities
- `backend/scripts/seed.py` — seeds 3 workflow runs + 7 drift reports for cold-start demo

## Key Integration Points

- **LLM fallback**: `LLMService.generate_structured()` checks `OPENAI_API_KEY`; if unset, returns realistic keyword-matched JSON. All agents work offline.
- **Risk gate**: `RiskAgent` compares `abs(cvar_95)` against `settings.RISK_CVAR_LIMIT` (default 0.05). With aggressive strategies, the gate genuinely fires.
- **Drift detection flow**: statistical methods (KS + PSI) are stateless and run immediately; autoencoder requires `POST /drift/train-model` first, then `POST /drift/detect-anomalies`.
- **DB auto-created**: `create_tables()` runs at startup via SQLAlchemy `metadata.create_all`. No migration step needed for local dev; for prod use Alembic.
- **Frontend↔API**: `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) must be set; CORS is configured in backend for `localhost:3000`.

---

## v2 — "The Honest Quant Copilot" (current architecture)

The platform was transformed from a scripted demo into an agentic, anti-overfitting research
copilot with a live monitoring + paper-trading loop. Key changes:

### Rigor engine (`app/quant/`)
- `backtester.py` — **honest** backtest: transaction costs + slippage on turnover, IS/OOS split,
  walk-forward param sweep, SPY benchmark (alpha/beta/IR), honors strategy params. `deep=True` also
  runs the robustness suite and attaches `honesty`.
- `robustness.py` — Deflated Sharpe Ratio, PBO (CSCV), Monte-Carlo permutation test, parameter
  sensitivity, and `honesty_score()` → 0–100 score + verdict (Robust/Fragile/Likely Overfit) + reasons.
- `metrics.py` — adds `calmar_ratio`, `compute_benchmark_stats` (alpha/beta/IR/beats_benchmark).
- `paper_broker.py` — paper execution helpers + pre-trade CVaR risk gate.

### Agentic runtime (`app/agents/agent_runtime.py`)
- A single skeptical "quant PM" agent with OpenAI **function-calling** tools (`run_backtest`,
  `check_regime_drift`, `optimize_portfolio`, `finalize`) that streams events
  (`agent_start/thought/tool_call/tool_result/verdict/complete`). `manager.py` wraps it.
- Offline mock agent drives the **same real engines**, so the honesty verdict is genuine without a key.
- `LLMService.agent_turn()` runs one tool-calling turn; `is_live()` reports key presence.

### New endpoints (registered in `app/api/v1/api.py`)
- `agents.py` — adds `POST /agents/workflow/stream` (SSE). Non-stream `/workflow` kept.
- `monitoring.py` — `POST /monitoring/monitor`, `GET /monitored`, `GET /alerts`,
  `POST /monitored/{id}/check`, `POST /monitored/{id}/stop`.
- `paper.py` — `GET /paper/account`, `POST /paper/rebalance`, `GET /paper/trades`.

### Persistence + scheduler
- New models: `MonitoredStrategy`, `DriftAlert`, `PaperPosition`, `PaperTrade`, `PaperSnapshot`.
- `WorkflowRun` gains `honesty_score/verdict/recommendation/oos_sharpe/pbo/is_monitored`.
- `app/core/database.py` has an additive SQLite column shim (`_ensure_columns_sync`).
- `app/core/scheduler.py` — asyncio loop (started in `main.py` lifespan) runs regime checks +
  paper rebalances every `MONITOR_INTERVAL_MINUTES`.
- `app/services/monitoring_service.py` — builds reference/current return windows, `assess_regime()`.
- `market_data_service.py` — **Stooq CSV fallback + 30-min cache** so the demo survives yfinance outages.

### Frontend (`frontend/`)
- Design system: `app/globals.css` tokens + `components/ui.tsx` (Card, StatTile, ScoreGauge,
  VerdictBadge, Pct/Num). `lib/api.ts` has an SSE `streamWorkflow()` client + monitoring/paper clients.
- `app/agents/page.tsx` — **Research Canvas**: live agent trace + Honesty Report (gauge, reasons,
  IS/OOS, strategy-vs-SPY chart, parameter-sensitivity heatmap, drift, HRP allocation, promote CTA).
- New `app/monitoring/page.tsx` and `app/paper/page.tsx`. `app/page.tsx` redesigned as Command Center.

### New config (`app/core/config.py`)
`TXN_COST_BPS`, `SLIPPAGE_BPS`, `OOS_FRACTION`, `BENCHMARK_TICKER`, `MONITOR_INTERVAL_MINUTES`,
`PAPER_STARTING_CASH`.

### Composable signals (`app/quant/signals.py`)
- Strategies are no longer 3 fixed archetypes. A `SignalSpec` = entry/exit **rules** (indicator +
  operator + value) combined with `all`/`any` logic. Indicators: `price_vs_sma`, `price_vs_ema`,
  `rsi`, `macd_hist`, `roc`, `zscore`, `bollinger_pctb`, `sma_ratio`. Ops include comparisons and
  `cross_above`/`cross_below`.
- `evaluate_spec` → entry/exit boolean series; `validate_spec` is defensive (bad specs fall back to a
  preset); `preset_spec` keeps the old momentum/mean_reversion/trend_following behavior; `scale_spec`
  + `primary_window/threshold` drive the generic parameter sweep (PBO/DSR/sensitivity); `describe_spec`
  renders the human-readable blueprint.
- `backtester.run_backtest(signal_spec=...)` overrides the preset; result carries `spec`,
  `strategy_blueprint`, and `exposure`. The robustness suite wraps any composed spec, so richer
  signals can't escape the overfitting checks.
- Agent (`agent_runtime.py`) gets a `signal_spec` tool param (with a `_RULE_SCHEMA`) and is prompted to
  compose 1-4 entry / 1-3 exit rules; the offline mock composes specs via `_compose_spec`.
- Frontend Research Canvas renders a **Strategy Blueprint** card (`StrategyBlueprintCard`) listing the
  composed entry/exit rules + average exposure.
