"""Database connection and session management."""

import os
from contextlib import contextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlmodel import SQLModel

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Pool config
# ---------------------------------------------------------------------------

POOL_SIZE    = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))

# ---------------------------------------------------------------------------
# Async engine — FastAPI (asyncpg)
# ---------------------------------------------------------------------------

engine = create_async_engine(
    settings.database_url,          # postgresql+asyncpg://...
    echo=settings.database_echo,
    future=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=3600,
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ---------------------------------------------------------------------------
# Sync engine — Celery workers (psycopg2)
# Requires: pip install psycopg2-binary
# URL:  postgresql+psycopg2://user:pass@host/db  (settings.database_url_sync)
# ---------------------------------------------------------------------------

sync_engine = create_engine(
    settings.database_url_sync,     # postgresql+psycopg2://...
    echo=settings.database_echo,
    future=True,
    pool_size=2,
    max_overflow=5,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=300,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async session dependency for FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@contextmanager
def get_worker_session():
    """Sync session context manager for Celery workers.

    Usage:
        with get_worker_session() as session:
            tx = session.get(Transaction, tx_id)
    """
    session = SyncSessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# ---------------------------------------------------------------------------
# DB lifecycle
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db() -> None:
    """Close async database connections."""
    await engine.dispose()