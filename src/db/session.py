"""Database engine and session management for JanusDeck (PostgreSQL 18)."""

from __future__ import annotations

import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import get_config
from src.db.models import Base

logger = logging.getLogger("janus.db")

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def normalize_database_url(url: str) -> str:
    """Ensures asyncpg driver prefix is applied to postgresql connection URLs."""
    trimmed = url.strip()
    if trimmed.startswith("postgresql://"):
        return trimmed.replace("postgresql://", "postgresql+asyncpg://", 1)
    if trimmed.startswith("postgres://"):
        return trimmed.replace("postgres://", "postgresql+asyncpg://", 1)
    return trimmed


def get_engine() -> Optional[AsyncEngine]:
    """Retrieves or initializes the global AsyncEngine."""
    global _engine, _session_factory
    if _engine is not None:
        return _engine

    config = get_config()
    db_url = config.database.url

    if not db_url:
        logger.warning("DATABASE_URL is not configured. Running without persistent database.")
        return None

    normalized_url = normalize_database_url(db_url)
    # Mask password for logs
    safe_log_url = normalized_url
    if "@" in safe_log_url and "://" in safe_log_url:
        proto, rest = safe_log_url.split("://", 1)
        creds, host_part = rest.split("@", 1)
        user = creds.split(":", 1)[0]
        safe_log_url = f"{proto}://{user}:****@{host_part}"

    logger.info("Connecting to PostgreSQL at %s", safe_log_url)
    _engine = create_async_engine(
        normalized_url,
        echo=False,
        future=True,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return _engine


def get_session_factory() -> Optional[async_sessionmaker[AsyncSession]]:
    """Returns the active async sessionmaker factory."""
    if _session_factory is None:
        get_engine()
    return _session_factory


async def init_db() -> bool:
    """Creates database tables if they do not exist."""
    engine = get_engine()
    if engine is None:
        return False

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized successfully.")
        return True
    except Exception as exc:
        logger.error("Failed to initialize database schema: %s", exc)
        raise exc


async def close_db():
    """Closes all database connections."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine closed.")


async def get_db() -> AsyncGenerator[Optional[AsyncSession], None]:
    """FastAPI dependency for obtaining an async database session."""
    factory = get_session_factory()
    if factory is None:
        yield None
        return

    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
