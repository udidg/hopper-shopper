"""Async SQLAlchemy engine & session factory with production-grade pool config."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    # ── Connection pool hardening ──
    pool_pre_ping=True,       # Validate connections before use (detects stale/dead conns)
    pool_size=5,              # Base pool size
    max_overflow=10,          # Extra connections under load
    pool_recycle=1800,        # Recycle connections every 30 min (prevent stale)
    pool_timeout=30,          # Wait up to 30s for a connection from the pool
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def dispose_engine() -> None:
    """Dispose the engine and close all pooled connections.

    Call this on application shutdown to avoid dangling connections.
    """
    await engine.dispose()
