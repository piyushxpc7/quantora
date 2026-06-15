from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer
from sqlalchemy.sql import func
from app.core.database import Base


class DriftReport(Base):
    __tablename__ = "drift_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feature_name = Column(String, default="default")

    # Statistical results
    ks_statistic = Column(Float, nullable=True)
    ks_p_value = Column(Float, nullable=True)
    ks_drift = Column(Boolean, nullable=True)

    psi_value = Column(Float, nullable=True)
    psi_drift = Column(Boolean, nullable=True)

    overall_drift = Column(Boolean, nullable=True)
    severity = Column(String, nullable=True)  # low / medium / high

    created_at = Column(DateTime(timezone=True), server_default=func.now())
