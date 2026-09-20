"""Saving agents and their version history."""

import pytest

from helpers import VALID_CONFIG
from vocalis.store import AgentNotFound, slugify


def config(name: str = "Support bot", **changes) -> dict:
    return {**VALID_CONFIG, "name": name, **changes}


async def test_create_starts_at_version_one(store):
    saved = await store.create(config())

    assert (saved.name, saved.slug, saved.version) == ("Support bot", "support-bot", 1)
    assert saved.config["nodes"][0]["id"] == "vad"


async def test_saving_writes_a_new_version(store):
    await store.create(config())

    second = await store.save("support-bot", config(description="now with feeling"), note="tweak")

    assert second.version == 2
    assert (await store.get("support-bot")).config["description"] == "now with feeling"
    assert [(v.version, v.note) for v in await store.versions("support-bot")] == [
        (2, "tweak"),
        (1, None),
    ]


async def test_old_versions_are_kept_intact(store):
    await store.create(config())
    await store.save("support-bot", config(name="Renamed"))

    first = await store.version("support-bot", 1)

    assert first.config["name"] == "Support bot"
    assert (await store.get("support-bot")).name == "Renamed"


async def test_restore_moves_history_forward(store):
    await store.create(config())
    await store.save("support-bot", config(description="second"))

    restored = await store.restore("support-bot", 1)

    assert restored.version == 3
    assert "description" not in restored.config
    assert [v.version for v in await store.versions("support-bot")] == [3, 2, 1]
    assert (await store.versions("support-bot"))[0].note == "restored version 1"


async def test_list_shows_the_current_version(store):
    await store.create(config("Support bot"))
    await store.create(config("Sales bot"))
    await store.save("support-bot", config("Support bot"))

    listed = {summary.slug: summary.version for summary in await store.list_agents()}

    assert listed == {"support-bot": 2, "sales-bot": 1}


async def test_agents_with_the_same_name_get_their_own_slug(store):
    first = await store.create(config("Support bot"))
    second = await store.create(config("Support bot"))

    assert (first.slug, second.slug) == ("support-bot", "support-bot-2")


async def test_delete_takes_the_versions_with_it(store):
    await store.create(config())

    await store.delete("support-bot")

    with pytest.raises(AgentNotFound):
        await store.get("support-bot")


@pytest.mark.parametrize(
    ("name", "slug"),
    [("Support bot", "support-bot"), ("  Héllo!! ", "h-llo"), ("...", "agent")],
)
def test_slugify(name, slug):
    assert slugify(name) == slug


async def test_missing_agent_and_version(store):
    await store.create(config())

    with pytest.raises(AgentNotFound, match='no agent called "nope"'):
        await store.get("nope")
    with pytest.raises(AgentNotFound, match="has no version 7"):
        await store.version("support-bot", 7)


async def test_migrations_match_the_models(database_url):
    """A model change without a migration would break a real deployment silently."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from vocalis.store import Base, create_engine

    engine = create_engine(database_url)
    try:
        async with engine.connect() as connection:
            differences = await connection.run_sync(
                lambda sync: compare_metadata(MigrationContext.configure(sync), Base.metadata)
            )
    finally:
        await engine.dispose()

    assert differences == []
