# 💎 QUANTORA — The Honest Quant Copilot

**Quantora is an AI quant copilot that proves whether a trading strategy actually works — then watches it decay live and paper-trades the survivors.**

Most backtesting tools happily hand you a beautiful in-sample equity curve that's a lie. Quantora does the opposite: a skeptical AI agent *tries to disprove your edge* before approving it, using out-of-sample testing, trading costs, and a real overfitting battery — then distills it all into a single **Honesty Score**.

> Describe a strategy in plain English → watch the agent research it live → get a brutally honest verdict → promote survivors to live monitoring and risk-gated paper trading.

---

## 🎯 Why it's different

The #1 killer of retail and small-fund quant strategies isn't a bad idea — it's **overfitting and silent regime decay**. Quantora is built squarely around that problem:

| Most tools | Quantora |
|---|---|
| In-sample backtest, no costs | Out-of-sample split, transaction costs + slippage, benchmark vs SPY |
| "Sharpe 2.1 🚀" | **Deflated Sharpe**, **Probability of Backtest Overfitting (PBO)**, permutation test |
| LLM writes a glowing summary | Agent *tries to reject* the strategy and explains why |
| Fire-and-forget | Approved strategies are **monitored for regime drift** and **paper-traded through a risk gate** |

---

## ✨ Core features

### 🔬 The Honesty Engine
Every backtest runs a full anti-overfitting battery and folds it into a **0–100 Honesty Score** with a verdict (*Robust / Fragile / Likely Overfit*) and plain-English reasons:
- **Out-of-sample decay** — how much in-sample Sharpe survives on unseen data
- **Deflated Sharpe Ratio** — Sharpe haircut for multiple-testing, skew & kurtosis (Bailey & López de Prado)
- **Probability of Backtest Overfitting (PBO)** — via Combinatorially Symmetric Cross-Validation
- **Monte-Carlo permutation test** — is the edge skill or luck?
- **Parameter sensitivity heatmap** — robust surface vs cherry-picked spike
- **Cost & benchmark reality** — net-of-cost CAGR, alpha/beta, information ratio

### 🤖 An agent that actually decides
A single skeptical "quant PM" powered by **OpenAI function-calling**. It **composes signals rule-by-rule** (8 indicators, AND/OR logic — not three canned presets), runs the honest backtest, reads the verdict, *tries a structurally different idea if it's overfit*, checks regime drift, sizes with HRP, and finalizes a recommendation — all **streamed live** to the UI (thoughts → tool calls → verdict).

> **Works fully offline.** With no API key, a scripted mock agent drives the *same real quant engines*, so the honesty verdict is genuine even without OpenAI.

### 📡 Live regime monitoring
Approved strategies are promoted to a watchlist. A background scheduler periodically compares the **live market regime against the validated one** (PSI + KS-test) and raises **regime-shift alerts** — the early-warning signal that a strategy is decaying.

### 💼 Risk-gated paper trading
Survivors are paper-traded (no real money). Every rebalance passes a **pre-trade CVaR risk gate** that *blocks* breaching trades and logs them to a blotter.

---

## 🧱 Tech stack

- **Backend:** FastAPI · async SQLAlchemy (SQLite dev / Postgres-ready) · pandas/numpy/scipy · PyTorch (drift autoencoder) · PyPortfolioOpt · OpenAI
- **Frontend:** Next.js 16 (App Router) · React 19 · Tailwind v4 · Recharts · lucide-react
- **Data:** yfinance (free) with a **Stooq fallback + cache** so the demo survives outages
- **Streaming:** Server-Sent Events for the live agent trace

---

## 🚀 Getting started

### Prerequisites
- Python 3.9+ · Node.js 18+

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload          # http://localhost:8000  (docs at /docs)
# optional: richer cold-start demo data
python -m scripts.seed
```

### Frontend
```bash
cd frontend
npm install
npm run dev                         # http://localhost:3000
```

### Configuration
Copy `.env.example` to `.env`. **`OPENAI_API_KEY` is optional** — leave it blank to run the full pipeline offline with the mock agent. SQLite tables auto-create on first boot; no migration step needed for local dev.

### Docker (full stack incl. TimescaleDB)
```bash
cp .env.example .env
docker-compose up --build
```

---

## 🗺️ How a strategy moves through Quantora

```
Plain-English idea
      │
      ▼
🤖 Research Copilot ──► composes a signal spec, runs the HONEST backtest
      │                 (costs · OOS split · benchmark · robustness suite)
      ▼
🔬 Honesty Score + verdict  ──►  Likely Overfit → rejected
      │ Robust / Fragile
      ▼
📡 Live Monitoring  ──►  PSI/KS regime checks → drift alerts on decay
      │
      ▼
💼 Paper Trading  ──►  HRP allocation, pre-trade CVaR risk gate, blotter
```

---

## 📁 Project layout

```
backend/
  app/quant/         backtester · robustness · signals (DSL) · metrics · portfolio · paper_broker
  app/agents/        agent_runtime (tool-calling loop) · manager
  app/services/      llm · market_data · drift_detection · monitoring · feature_engineering
  app/api/v1/        agents (+SSE) · monitoring · paper · drift · market-data · stream
  app/models/        workflow · drift · monitoring · paper
  app/core/          config · database · scheduler
frontend/
  app/               page (Command Center) · agents (Research Canvas) · monitoring · paper · drift
  components/        ui (design system) · Sidebar · DriftChart
  lib/api.ts         typed client incl. SSE streamWorkflow
```

See **CLAUDE.md** for a detailed architecture walkthrough.

---

## 📄 License

MIT
