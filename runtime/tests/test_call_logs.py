"""Call logs: what a finished call leaves behind."""

import copy

import pytest
import pytest_asyncio

from helpers import VALID_CONFIG
from vocalis.store import CallStore, create_engine, create_session_factory


@pytest_asyncio.fixture
async def logs(database_url):
    engine = create_engine(database_url)
    try:
        yield CallStore(create_session_factory(engine))
    finally:
        await engine.dispose()


def turn(number: int, total_ms: int, interrupted: bool = False) -> dict:
    return {
        "type": "turn",
        "turn": number,
        "total_ms": total_ms,
        "interrupted": interrupted,
        "stages": [
            {"key": "tts_ttfb", "label": "speech synthesis", "node_id": "tts", "ms": total_ms}
        ],
    }


async def record_call(logs: CallStore, call_id: str = "call0001", **kwargs) -> None:
    await logs.start(call_id, copy.deepcopy(VALID_CONFIG), **kwargs)


async def test_a_call_records_its_turns_and_transcript(logs):
    await record_call(logs, slug="test-agent", version=3)
    await logs.add_message("call0001", {"role": "user", "text": "Hello"})
    await logs.add_message("call0001", {"role": "agent", "text": "Hi", "interrupted": True})
    await logs.add_turn("call0001", turn(1, 900))
    await logs.finish("call0001")

    detail = await logs.get("call0001")

    assert detail.summary.agent_slug == "test-agent"
    assert detail.summary.agent_version == 3
    assert detail.summary.turn_count == 1
    assert [message["text"] for message in detail.messages] == ["Hello", "Hi"]
    assert detail.messages[1]["interrupted"] is True
    assert detail.turns[0]["stages"][0]["node_id"] == "tts"


async def test_the_config_that_ran_is_kept(logs):
    """An agent can be edited between calls; a comparison needs what actually ran."""
    await record_call(logs, slug="test-agent")

    detail = await logs.get("call0001")

    assert detail.config["nodes"][1]["provider"] == "fake"


async def test_finishing_stores_the_percentiles(logs):
    await record_call(logs)
    for number, ms in enumerate([500, 700, 900, 4000], start=1):
        await logs.add_turn("call0001", turn(number, ms, interrupted=ms == 4000))
    await logs.finish("call0001")

    [summary] = await logs.list()

    assert (summary.turn_count, summary.interrupted_turns) == (4, 1)
    assert summary.p50_ms == 700
    assert summary.p95_ms == 4000
    assert summary.ended_at is not None


async def test_listing_filters_by_agent(logs):
    await record_call(logs, "call0001", slug="support-bot")
    await record_call(logs, "call0002", slug="sales-bot")

    assert [call.agent_slug for call in await logs.list(slug="sales-bot")] == ["sales-bot"]
    assert len(await logs.list()) == 2


async def test_stats_for_one_agent(logs):
    await record_call(logs, "call0001", slug="support-bot")
    await logs.add_turn("call0001", turn(1, 800))
    await logs.add_turn("call0001", turn(2, 600))
    await logs.finish("call0001")

    assert await logs.stats("support-bot") == {"calls": 1, "turns": 2, "median_ms": 600}


async def test_deleting_a_call_takes_its_turns(logs):
    await record_call(logs)
    await logs.add_turn("call0001", turn(1, 800))

    assert await logs.delete("call0001") is True
    assert await logs.get("call0001") is None
    assert await logs.delete("call0001") is False


async def test_an_unknown_call(logs):
    assert await logs.get("nosuchcall") is None


@pytest.mark.parametrize("totals", [[], [100]])
async def test_percentiles_with_few_turns(logs, totals):
    await record_call(logs)
    for number, ms in enumerate(totals, start=1):
        await logs.add_turn("call0001", turn(number, ms))
    await logs.finish("call0001")

    [summary] = await logs.list()
    assert summary.p50_ms == (totals[0] if totals else None)


async def test_overview_summarises_recent_calls(logs):
    await record_call(logs, "call0001", slug="support-bot")
    for number, ms_value in enumerate([600, 900, 3000], start=1):
        await logs.add_turn("call0001", turn(number, ms_value, interrupted=ms_value == 3000))
    await logs.finish("call0001")

    overview = await logs.overview()

    assert (overview.calls, overview.turns) == (1, 3)
    assert overview.p50_ms == 900
    assert overview.p95_ms == 3000
    assert overview.interrupted_share == round(1 / 3, 3)
    assert [day["calls"] for day in overview.daily] == [1]
    # The stage that costs the most is what the home page points at.
    assert overview.slowest_stages[0]["node_id"] == "tts"
    assert [call.id for call in overview.recent] == ["call0001"]


async def test_overview_with_no_calls(logs):
    overview = await logs.overview()

    assert (overview.calls, overview.turns, overview.p50_ms) == (0, 0, None)
    assert overview.interrupted_share == 0.0
    assert overview.slowest_stages == []
