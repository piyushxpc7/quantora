from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

_url = settings.DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in _url else {}

engine = create_async_engine(_url, echo=False, future=True, connect_args=_connect_args)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


def _ensure_columns_sync(conn):
    """Additive, no-op-if-present column migration for SQLite dev DBs (create_all
    never ALTERs existing tables). Each entry is (table, column, SQL type)."""
    from sqlalchemy import text
    additions = [
        ("workflow_runs", "honesty_score", "FLOAT"),
        ("workflow_runs", "verdict", "VARCHAR"),
        ("workflow_runs", "recommendation", "VARCHAR"),
        ("workflow_runs", "oos_sharpe", "FLOAT"),
        ("workflow_runs", "pbo", "FLOAT"),
        ("workflow_runs", "is_monitored", "BOOLEAN"),
    ]
    existing = {}
    for table, column, coltype in additions:
        if table not in existing:
            try:
                rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                existing[table] = {r[1] for r in rows}
            except Exception:
                existing[table] = set()
        if existing[table] and column not in existing[table]:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))
                existing[table].add(column)
            except Exception:
                pass


async def create_tables():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            if "sqlite" in _url:
                await conn.run_sync(_ensure_columns_sync)
        print("Database tables ready.")
    except Exception as e:
        print(f"Warning: DB unavailable ({e}). Persistence disabled; app still functional.")


async def dispose_engine():
    await engine.dispose()
