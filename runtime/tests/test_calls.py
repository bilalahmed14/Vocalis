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
    return Call(
        id="call-1",
        pc_id="SmallWebRTCConnection#0-abc",
        agent_name="Test agent",
        slug="test-agent",
        tracer=CallTracer(agent),
    )


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
    call = manager._create("call-1", "pc#0", parse_config(config), agent, slug=None)

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


class FakeHandler:
    """Stands in for Pipecat's WebRTC handler, which needs a real browser."""

    def __init__(self):
        self.request = None

    async def handle_web_request(self, request, webrtc_connection_callback):
        self.request = request
        connection = type("FakeConnection", (), {"pc_id": "pc-7"})()
        await webrtc_connection_callback(connection)
        return {"sdp": "v=0 answer", "type": "answer", "pc_id": connection.pc_id}


async def test_starting_a_call_answers_the_offer_and_registers_the_call(
    config, registry, env, monkeypatch
):
    from vocalis import parse_config
    from vocalis.calls import SmallWebRTCRequest

    for name, value in env.items():
        monkeypatch.setenv(name, value)
    handler = FakeHandler()
    manager = CallManager(registry, handler=handler)

    answer = await manager.start(
        parse_config(config), SmallWebRTCRequest(sdp="v=0 offer", type="offer"), slug="test-agent"
    )

    assert answer["type"] == "answer"
    assert handler.request.sdp == "v=0 offer"

    [call] = manager.calls
    # The call id is ours and URL-safe; Pipecat's pc_id contains a '#'.
    assert call.id == answer["call_id"] != call.pc_id
    assert "#" not in call.id
    assert call.snapshot() == {
        "id": call.id,
        "pc_id": "pc-7",
        "agent_name": "Test agent",
        "slug": "test-agent",
        "state": "connecting",
        "turns": 0,
    }
    await manager.shutdown()


async def test_a_config_that_cannot_compile_never_reaches_the_browser(config, registry, env):
    """The caller should hear a refusal, not silence on an answered call."""
    from vocalis import ConfigError, parse_config
    from vocalis.calls import SmallWebRTCRequest

    handler = FakeHandler()
    config["nodes"][2]["provider"] = "nope"

    with pytest.raises(ConfigError):
        await CallManager(registry, handler=handler).start(
            parse_config(config), SmallWebRTCRequest(sdp="v=0", type="offer")
        )

    assert handler.request is None


async def test_a_call_writes_a_log(config, registry, env, monkeypatch, database_url):
    """What the dashboard shows live and what the log keeps must be the same call."""
    from vocalis import parse_config
    from vocalis.calls import SmallWebRTCRequest
    from vocalis.store import CallStore, create_engine, create_session_factory

    for name, value in env.items():
        monkeypatch.setenv(name, value)

    engine = create_engine(database_url)
    logs = CallStore(create_session_factory(engine))
    manager = CallManager(registry, handler=FakeHandler(), call_store=logs)

    try:
        answer = await manager.start(
            parse_config(config),
            SmallWebRTCRequest(sdp="v=0", type="offer"),
            slug="test-agent",
            version=2,
            raw_config=config,
        )
        [call] = manager.calls
        call.publish({"type": "transcript", "role": "user", "text": "Hello"})
        call.publish(
            {"type": "turn", "turn": 1, "total_ms": 900, "interrupted": False, "stages": []}
        )
        await manager.hangup(call.id)

        detail = await logs.get(answer["call_id"])
        assert detail.summary.agent_slug == "test-agent"
        assert detail.summary.agent_version == 2
        assert detail.summary.turn_count == 1
        assert detail.summary.p50_ms == 900
        assert [message["text"] for message in detail.messages] == ["Hello"]
    finally:
        await engine.dispose()
