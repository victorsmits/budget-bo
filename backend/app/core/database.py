"""Database connection and session management."""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.core.config import get_settings

settings = get_settings()

# Pool configuration
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))

# Create async engine with connection pool (for FastAPI - single event loop)
engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    future=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=3600,
    pool_pre_ping=True,
)

# Session factory for FastAPI (single event loop)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


def create_worker_session() -> AsyncSession:
    """Create a fresh engine + session for Celery worker tasks.

    Each call to asyncio.run() in a Celery task creates a new event loop.
    The module-level engine holds connections tied to a previous loop,
    causing 'Future attached to a different loop' errors.
    This function creates a disposable engine per task to avoid that.
    """
    worker_engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        future=True,
        pool_size=2,
        max_overflow=5,
        pool_timeout=POOL_TIMEOUT,
        pool_recycle=300,
        pool_pre_ping=True,
    )
    factory = sessionmaker(
        bind=worker_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    return factory()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
