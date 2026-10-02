"""Turn tracing: mapping Pipecat's latency breakdown onto the agent's nodes."""

import pytest
from pipecat.observers.user_bot_latency_observer import (
    LatencyBreakdown,
    LatencyContribution,
    LatencyOwnerKind,
    MeasuredFrom,
)

from vocalis import compile_agent, parse_config
from vocalis.tracing import CallTrace, CallTracer
from vocalis.tracing.model import Stage, TurnTrace


def contribution(key: str, owner: str, secs: float, kind=LatencyOwnerKind.SERVICE):
    return LatencyContribution(
        key=key,
        label=key.replace("_", " "),
        owner=owner,
        owner_kind=kind,
        start_time=0.0,
        duration_secs=secs,
    )


@pytest.fixture
def agent(config, registry, env):
    return compile_agent(parse_config(config), registry, env)


def breakdown_for(agent, *contributions) -> LatencyBreakdown:
    return LatencyBreakdown(
        contributions=list(contributions),
        measured_from=MeasuredFrom.USER_SILENCE,
    )


def test_stages_are_attributed_to_nodes(agent):
    tracer = CallTracer(agent)
    names = {compiled.node.id: compiled.processor.name for compiled in agent.nodes}

    tracer._record(
        breakdown_for(
            agent,
            contribution("vad_silence", "config:stop_secs", 0.2, LatencyOwnerKind.SETTING),
            contribution("stt", names["stt"], 0.1),
            contribution("llm_ttfb", names["llm"], 0.4),
            contribution("tts_ttfb", names["tts"], 0.3),
        )
    )

    [turn] = tracer.call.turns
    assert [stage.node_id for stage in turn.stages] == [None, "stt", "llm", "tts"]
    assert turn.total_ms == pytest.approx(1000)
    assert turn.by_node() == {
        "stt": pytest.approx(0.1),
        "llm": pytest.approx(0.4),
        "tts": pytest.approx(0.3),
    }


def test_time_no_node_owns_is_still_reported(agent):
    """The silence a VAD waits out is latency too, and the usual place it hides."""
    tracer = CallTracer(agent)

    tracer._record(
        breakdown_for(
            agent,
            contribution("vad_silence", "config:stop_secs", 0.8, LatencyOwnerKind.SETTING),
        )
    )

    [stage] = tracer.call.turns[0].stages
    assert stage.node_id is None
    assert stage.owner == "config:stop_secs"
    assert stage.ms == pytest.approx(800)


def test_turns_are_reported_as_they_finish(agent):
    seen = []
    tracer = CallTracer(agent, on_turn=seen.append)

    tracer._record(breakdown_for(agent, contribution("llm_ttfb", "x", 0.5)))

    assert [turn.total_ms for turn in seen] == [pytest.approx(500)]


def test_summary_across_turns():
    call = CallTrace()
    for total, tts in [(1.0, 0.5), (2.0, 1.4), (1.2, 0.6)]:
        call.add(
            TurnTrace(
                turn=1,
                total_secs=total,
                stages=(
                    Stage("tts_ttfb", "tts ttfb", "CartesiaTTSService#0", tts, node_id="tts"),
                    Stage("llm_ttfb", "llm ttfb", "OpenAILLMService#0", total - tts, node_id="llm"),
                ),
            )
        )

    assert call.percentile(0.5) == pytest.approx(1200)
    assert max(call.totals_ms) == pytest.approx(2000)

    slowest, median_ms = call.slowest_stages()[0]
    assert "tts" in slowest
    assert median_ms == pytest.approx(600)


def test_interruptions_are_recorded(agent):
    tracer = CallTracer(agent)
    tracer._turn_number = 3
    tracer._interrupted[3] = True

    tracer._record(breakdown_for(agent, contribution("llm_ttfb", "x", 0.2)))

    assert tracer.call.turns[0].interrupted


def test_throughput_turns_usage_into_a_rate():
    """Latency alone can't separate a fast model from a terse one."""
    from vocalis.tracing.throughput import Work

    assert Work(tokens=120).rate(2.0) == {"tokens_per_sec": 60.0}
    assert Work(characters=380).rate(1.0) == {"chars_per_sec": 380.0}
    # Above 1 means speech was generated faster than it plays, which a call needs.
    assert Work(audio_seconds=3.4).rate(2.0) == {"realtime_factor": 1.7}
    assert Work().rate(1.0) == {}
    assert Work(tokens=10).rate(0) == {}


async def test_stages_carry_what_the_model_produced(agent):
    tracer = CallTracer(agent)
    names = {compiled.node.id: compiled.processor.name for compiled in agent.nodes}
    from vocalis.tracing.throughput import Work

    tracer._throughput._work = {names["llm"]: Work(tokens=90)}

    tracer._record(breakdown_for(agent, contribution("llm_ttfb", names["llm"], 1.5)))

    [stage] = tracer.call.turns[0].stages
    assert stage.throughput == {"tokens_per_sec": 60.0}


async def test_usage_is_not_carried_into_the_next_turn(agent):
    from vocalis.tracing.throughput import Work

    tracer = CallTracer(agent)
    names = {compiled.node.id: compiled.processor.name for compiled in agent.nodes}
    tracer._throughput._work = {names["llm"]: Work(tokens=90)}

    tracer._record(breakdown_for(agent, contribution("llm_ttfb", names["llm"], 1.0)))
    tracer._record(breakdown_for(agent, contribution("llm_ttfb", names["llm"], 1.0)))

    assert tracer.call.turns[0].stages[0].throughput == {"tokens_per_sec": 90.0}
    assert tracer.call.turns[1].stages[0].throughput == {}
