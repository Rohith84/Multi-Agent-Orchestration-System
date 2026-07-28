"""
Async SQLAlchemy database engine and session management.

Provides:
- Async engine and session factory
- Declarative Base for models
- Dependency injection helper for FastAPI
- DB initialization and teardown
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()
print(f"[DEBUG ENGINE] Created engine with URL: {settings.database_url}")

# Async engine — pool settings tuned for development
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """
    Declarative base for all SQLAlchemy models.

    All models should inherit from this class.
    Alembic auto-generates migrations by inspecting Base.metadata.
    """

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Initialize database — create all tables from Base metadata.

    Called during application startup via the lifespan handler.
    In production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose of the database engine on shutdown."""
    await engine.dispose()
