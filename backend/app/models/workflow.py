from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON, Integer
from sqlalchemy.sql import func
from app.core.database import Base


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_request = Column(String, nullable=False)
    strategy_name = Column(String, nullable=True)
    universe = Column(JSON, nullable=True)
    signal_type = Column(String, nullable=True)

    # Backtest metrics
    cagr = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    var_95 = Column(Float, nullable=True)
    cvar_95 = Column(Float, nullable=True)

    # Risk gate
    risk_approved = Column(Boolean, nullable=True)

    # Honesty / robustness verdict
    honesty_score = Column(Float, nullable=True)
    verdict = Column(String, nullable=True)        # Robust / Fragile / Likely Overfit
    recommendation = Column(String, nullable=True)  # approve / reject
    oos_sharpe = Column(Float, nullable=True)
    pbo = Column(Float, nullable=True)

    # Portfolio
    final_allocation = Column(JSON, nullable=True)
    optimization_method = Column(String, nullable=True)

    # Live monitoring
    is_monitored = Column(Boolean, default=False)

    # Full event log for the research canvas (replayable)
    workflow_log = Column(JSON, nullable=True)

    status = Column(String, default="completed")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
