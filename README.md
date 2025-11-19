# 💎 QUANTORA — AI-Driven Quantitative Finance Ecosystem

**Quantora** is a modular, multi-agent platform designed to revolutionize quantitative finance by integrating strategy generation, portfolio optimization, risk management, and model monitoring into a single, powerful ecosystem.

Think of it as **“Bloomberg + QuantConnect + RiskMetrics + AutoGPT for quantitative finance.”**

---

## 🔥 Core Vision

Quantora addresses three critical pain points in the industry:
1.  **Slow Strategy Discovery**: Automates research using multi-agent LLMs.
2.  **Reactive Risk Management**: Proactively detects model drift and regime shifts using state-of-the-art AI.
3.  **Fragmented Tooling**: Unifies data, backtesting, and risk into one cohesive SaaS platform.

---

## 🧠 Architecture

Quantora is built on a robust, multi-layer architecture:

### **Layer 1: Data & Ingestion Engine**
- **Sources**: Live feeds (Alpaca, Zerodha), Historical Data, Macro Indicators (FRED), On-chain data.
- **Tech**: FastAPI, WebSockets, TimescaleDB/PostgreSQL.

### **Layer 2: QuantoraDrift (Model Monitoring)**
*The Star Component* - Real-time detection of model decay and market regime shifts.
- **Methods**:
    - **Statistical**: PSI, KS Test, Wasserstein Distance.
    - **AI/Deep Learning**: Transformer-based anomaly detection, Autoencoders for reconstruction error, LLM-based regime analysis.
- **Output**: Automated alerts on feature distribution changes and performance decay.

### **Layer 3: Multi-Agent Quant AI System**
Four specialized agents working in concert:
1.  **Strategy Research Agent**: Generates novel trading strategies using LLMs.
2.  **Backtesting Agent**: Validates strategies against historical data.
3.  **Risk Agent**: Calculates VaR, CVaR, and runs stress tests.
4.  **Portfolio Optimization Agent**: Balances risk/reward using Black-Litterman, HRP, and Kelly Criterion.

### **Layer 4: Execution & Position Management**
- Paper trading and live execution capabilities.
- Risk-based trade blocking (e.g., "Block trade if CVaR > limit").

### **Layer 5: Frontend Web UI**
- **Tech**: Next.js, React, Tailwind CSS.
- **Features**: Interactive dashboards for market overview, backtesting results, drift monitoring, and agent chat.

### **System Architecture**

```mermaid
graph TD
    User[User / Quant] -->|Interacts| UI[Frontend Web UI (Next.js)]
    UI -->|API Requests| API[FastAPI Backend]
    
    subgraph "Layer 1: Data & Ingestion"
        API -->|Fetch| MarketData[Market Data Module]
        MarketData -->|Store/Retrieve| DB[(TimescaleDB / Postgres)]
        External[External APIs: Alpaca, Yahoo, FRED] --> MarketData
    end
    
    subgraph "Layer 2: QuantoraDrift"
        Drift[Drift Detection Engine] -->|Monitor| Models[ML Models]
        Drift -->|Alerts| UI
    end
    
    subgraph "Layer 3: Multi-Agent System"
        API -->|Dispatch| Manager[Agent Manager]
        Manager --> Strat[Strategy Agent]
        Manager --> Backtest[Backtest Agent]
        Manager --> Risk[Risk Agent]
        Manager --> Portfolio[Portfolio Agent]
    end
    
    subgraph "Layer 4: Execution"
        Portfolio -->|Orders| Execution[Execution Engine]
        Execution -->|Trade| External
    end
```

---

## 🧩 Modules

1.  **Market Data Module**: OHLCV fetching, technical indicator computation.
2.  **Feature Engineering**: Automated feature generation (volatility, lag, macro).
3.  **ML Modeling**: LSTM, GRU, Temporal Fusion Transformers, Neural SDEs.
4.  **QuantoraDrift**: Advanced drift detection (Concept drift, Covariate shift).
5.  **Strategy Evaluation**: Walk-forward optimization, Cross-validation.
6.  **Portfolio Optimization**: Mean-Variance, HRP, Black-Litterman.
7.  **Risk & Stress Testing**: Monte Carlo simulations, Liquidity risk.
8.  **Automated Reporting**: PDF generation, Daily risk summaries.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker (optional)

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/quantora.git
    cd quantora
    ```

2.  **Backend Setup**
    ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    uvicorn main:app --reload
    ```

3.  **Frontend Setup**
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

---

## 📄 License

MIT License.
