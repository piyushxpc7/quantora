from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class MonitoredStrategy(Base):
    """An approved strategy promoted to live regime monitoring."""
    __tablename__ = "monitored_strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, nullable=True)
    name = Column(String, nullable=True)
    universe = Column(JSON, nullable=True)
    signal_type = Column(String, nullable=True)
    strategy_params = Column(JSON, nullable=True)
    honesty_score = Column(Float, nullable=True)

    # Reference return distribution captured at promotion (the "normal" regime).
    reference_returns = Column(JSON, nullable=True)

    latest_psi = Column(Float, nullable=True)
    regime_status = Column(String, default="ok")  # ok / watch / shifted
    active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_checked = Column(DateTime(timezone=True), nullable=True)


class DriftAlert(Base):
    """A regime-shift alert raised against a monitored strategy."""
    __tablename__ = "drift_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey("monitored_strategies.id"), nullable=True)
    strategy_name = Column(String, nullable=True)
    psi_value = Column(Float, nullable=True)
    ks_p_value = Column(Float, nullable=True)
    severity = Column(String, nullable=True)  # low / medium / high
    message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
