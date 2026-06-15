from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Quantora"
    API_V1_STR: str = "/api/v1"

    # LLM
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./quantora.db"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Risk limits
    RISK_CVAR_LIMIT: float = 0.05  # halt workflow if CVaR > 5%

    # Backtest realism
    TXN_COST_BPS: float = 5.0   # commission/spread per turnover, basis points
    SLIPPAGE_BPS: float = 2.0   # execution slippage per turnover, basis points
    OOS_FRACTION: float = 0.30  # fraction of history reserved for out-of-sample
    BENCHMARK_TICKER: str = "SPY"

    # Monitoring
    MONITOR_INTERVAL_MINUTES: int = 30   # background drift/rebalance cadence
    PAPER_STARTING_CASH: float = 100_000.0

    class Config:
        env_file = (".env", "../.env")

settings = Settings()
