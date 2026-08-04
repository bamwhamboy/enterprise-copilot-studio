"""Async SQLAlchemy engine and session management.

The engine is created lazily and does not connect until first used, so
importing this module (or booting the app) never requires a live
PostgreSQL instance — useful for running the test suite and the
``/health`` liveness check without external dependencies.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped async database session.

    Not used by any route yet (``/health`` intentionally has no
    dependencies), but available for the first data-backed endpoint.
    """
    async with AsyncSessionLocal() as session:
        yield session


async def dispose_engine() -> None:
    """Cleanly dispose of the engine's connection pool on shutdown."""
    await engine.dispose()
