"""Database connection helpers."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DEFAULT_URL = "postgresql+asyncpg://vocalis:vocalis@localhost:5432/vocalis"


def database_url(url: str | None = None) -> str:
    """The database URL, with the async driver filled in.

    DATABASE_URL is usually written the libpq way ("postgresql://..."), which is what
    psql and most hosting providers hand out; SQLAlchemy needs the driver spelled out.
    """
    resolved = url or os.environ.get("DATABASE_URL") or DEFAULT_URL
    if resolved.startswith("postgresql://"):
        return resolved.replace("postgresql://", "postgresql+asyncpg://", 1)
    if resolved.startswith("postgres://"):
        return resolved.replace("postgres://", "postgresql+asyncpg://", 1)
    return resolved


def create_engine(url: str | None = None, **kwargs) -> AsyncEngine:
    return create_async_engine(database_url(url), **kwargs)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def engine_for(url: str | None = None, **kwargs) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(url, **kwargs)
    try:
        yield engine
    finally:
        await engine.dispose()
