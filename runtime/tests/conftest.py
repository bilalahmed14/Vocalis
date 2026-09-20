import copy
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from db import reachable, temporary_database
from helpers import VALID_CONFIG, write_provider
from vocalis import ProviderRegistry
from vocalis.store import AgentStore, create_engine, create_session_factory


@pytest.fixture
def config() -> dict[str, Any]:
    """A fresh, valid config dict that tests can break on purpose."""
    return copy.deepcopy(VALID_CONFIG)


@pytest.fixture
def providers_root(tmp_path: Path) -> Path:
    """A providers dir with one `fake` plugin per node type."""
    root = tmp_path / "providers"
    write_provider(root, "vad", "fake")
    write_provider(
        root,
        "stt",
        "fake",
        env=["FAKE_STT_KEY"],
        params={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "model": {"enum": ["small", "large"], "default": "large"},
                "language": {"type": "string", "default": "en"},
            },
        },
    )
    write_provider(root, "llm", "fake")
    write_provider(root, "llm", "other")
    write_provider(root, "tts", "fake")
    return root


@pytest.fixture
def registry(providers_root: Path) -> ProviderRegistry:
    return ProviderRegistry.from_directory(providers_root)


@pytest.fixture
def env() -> dict[str, str]:
    return {"FAKE_STT_KEY": "secret"}


@pytest_asyncio.fixture
async def database_url() -> str:
    """A migrated, empty database; skips the test when Postgres isn't running."""
    if not await reachable():
        pytest.skip("no Postgres running (see deploy/README.md)")
    async with temporary_database() as url:
        yield url


@pytest_asyncio.fixture
async def store(database_url: str) -> AgentStore:
    engine = create_engine(database_url)
    try:
        yield AgentStore(create_session_factory(engine))
    finally:
        await engine.dispose()
