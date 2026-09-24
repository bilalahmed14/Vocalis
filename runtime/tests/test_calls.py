"""Live calls: what the dashboard is told while a call is happening."""

import asyncio

import pytest

from vocalis.calls import Call, CallManager
from vocalis.tracing import CallTracer
from vocalis.tracing.model import Stage, TurnTrace


@pytest.fixture
def call(config, registry, env):
    from vocalis import compile_agent, parse_config

    agent = compile_agent(parse_config(config), registry, env)
    return Call(id="call-1", agent_name="Test agent", slug="test-agent", tracer=CallTracer(agent))


async def collect(call: Call, count: int) -> list[dict]:
    """Take the first `count` events from a watcher."""
    events = []
    async for event in call.watch():
        events.append(event)
        if len(events) >= count:
            break
    return events


async def test_watchers_get_the_state_first(call):
    [first] = await collect(call, 1)

    assert first == {"type": "state", "state": "connecting", "at": first["at"]}


async def test_events_reach_a_live_watcher(call):
    watcher = asyncio.create_task(collect(call, 3))
    await asyncio.sleep(0)  # let the watcher subscribe

    call.publish({"type": "transcript", "role": "user", "text": "Hello"})
    call.publish({"type": "turn", "turn": 1, "total_ms": 840})

    events = await asyncio.wait_for(watcher, timeout=2)

    assert [event["type"] for event in events] == ["state", "transcript", "turn"]
    assert events[1]["text"] == "Hello"
    assert all("at" in event for event in events)


async def test_a_watcher_joining_late_sees_what_it_missed(call):
    call.publish({"type": "transcript", "role": "user", "text": "Hello"})
    call.publish({"type": "transcript", "role": "agent", "text": "Hi there"})

    events = await collect(call, 3)

    assert [event["type"] for event in events] == ["state", "transcript", "transcript"]
    assert [event.get("text") for event in events[1:]] == ["Hello", "Hi there"]


async def test_watching_stops_when_the_call_ends(call):
    async def watch_to_the_end():
        return [event async for event in call.watch()]

    watcher = asyncio.create_task(watch_to_the_end())
    await asyncio.sleep(0)
    call.publish({"type": "state", "state": "ended"})

    events = await asyncio.wait_for(watcher, timeout=2)

    assert events[-1]["state"] == "ended"


async def test_turns_are_published_with_per_node_timings(config, registry, env):
    from vocalis import compile_agent, parse_config

    agent = compile_agent(parse_config(config), registry, env)
    manager = CallManager(registry)
    call = manager._create("call-1", parse_config(config), agent, slug=None)

    manager._on_turn(
        "call-1",
        TurnTrace(
            turn=2,
            total_secs=0.84,
            stages=(
                Stage("vad_silence", "vad silence", "config:stop_secs", 0.2),
                Stage("tts_ttfb", "speech synthesis", "TTS#0", 0.64, node_id="tts"),
            ),
        ),
    )

    [event] = call.turns
    assert event["total_ms"] == 840
    assert event["by_node"] == {"tts": 640}
    assert event["stages"][0] == {
        "key": "vad_silence",
        "label": "vad silence",
        "owner": "config:stop_secs",
        "node_id": None,
        "ms": 200,
    }


async def test_hanging_up_an_unknown_call(registry):
    assert await CallManager(registry).hangup("nope") is False
