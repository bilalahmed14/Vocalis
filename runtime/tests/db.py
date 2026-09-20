"""A throwaway Postgres database for tests.

Skips (rather than fails) when no database is reachable, so the rest of the suite
still runs on a machine without Docker.
"""

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncEngine

from vocalis.store import create_engine, database_url

RUNTIME_DIR = Path(__file__).resolve().parents[1]


def server_url() -> str:
    """Where to reach Postgres, from VOCALIS_TEST_DATABASE_URL or DATABASE_URL."""
    return database_url(
        os.environ.get("VOCALIS_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    )


async def reachable() -> bool:
    engine = create_engine(server_url())
    try:
        async with engine.connect():
            return True
    except Exception:
        return False
    finally:
        await engine.dispose()


@asynccontextmanager
async def temporary_database() -> AsyncIterator[str]:
    """Create a database, migrate it, and drop it afterwards."""
    name = f"vocalis_test_{uuid.uuid4().hex[:12]}"
    admin: AsyncEngine = create_engine(server_url(), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as connection:
            await connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
    except Exception as e:  # pragma: no cover - depends on the developer's machine
        await admin.dispose()
        pytest.skip(f"no Postgres for tests ({e.__class__.__name__}); start it with docker compose")

    url = server_url().rsplit("/", 1)[0] + f"/{name}"
    # Alembic's env.py runs its own event loop, so keep it off this one.
    await asyncio.to_thread(migrate, url)
    try:
        yield url
    finally:
        async with admin.connect() as connection:
            await connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await admin.dispose()


def migrate(url: str) -> None:
    """Run the real migrations, so tests exercise what production runs."""
    config = Config(str(RUNTIME_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(RUNTIME_DIR / "migrations"))
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
