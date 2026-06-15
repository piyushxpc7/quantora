from sqlalchemy import Column, String, Float, DateTime, Integer
from sqlalchemy.sql import func
from app.core.database import Base


class PaperPosition(Base):
    __tablename__ = "paper_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, nullable=False, unique=True)
    shares = Column(Float, default=0.0)
    avg_price = Column(Float, default=0.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, nullable=False)
    side = Column(String, nullable=False)         # buy / sell
    shares = Column(Float, default=0.0)
    price = Column(Float, default=0.0)
    status = Column(String, default="filled")     # filled / blocked
    reason = Column(String, nullable=True)        # why blocked / source strategy
    strategy_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PaperSnapshot(Base):
    """Daily mark-to-market equity snapshot for the paper account curve."""
    __tablename__ = "paper_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equity = Column(Float, default=0.0)
    cash = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
