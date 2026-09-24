"""How traces are printed in the terminal."""

from vocalis.tracing import CallTrace
from vocalis.tracing.model import Stage, TurnTrace
from vocalis_cli.metrics import summary, turn_line, waterfall


def turn(total: float = 1.0, **kwargs) -> TurnTrace:
    return TurnTrace(
        turn=kwargs.pop("number", 1),
        total_secs=total,
        stages=kwargs.pop(
            "stages",
            (
                Stage("vad_silence", "vad silence", "config:stop_secs", 0.2),
                Stage("llm_ttfb", "llm ttfb", "OllamaLLM#0", 0.3, node_id="llm"),
                Stage("tts_ttfb", "tts ttfb", "DeepgramTTS#0", 0.5, node_id="tts"),
            ),
        ),
        **kwargs,
    )


def test_turn_line_reports_time_to_first_audio():
    assert turn_line(turn(1.2)) == "  turn 1: 1200 ms to first audio"


def test_interrupted_turns_are_flagged():
    assert turn_line(turn(interrupted=True)).endswith("[interrupted]")


def test_waterfall_names_the_node_and_scales_bars():
    lines = waterfall(turn())

    assert len(lines) == 3
    assert "[tts]" in lines[2] and "500 ms" in lines[2]
    # The longest stage gets the longest bar.
    assert lines[2].count("█") > lines[1].count("█") > lines[0].count("█")
    # Time no node owns still shows, named by the setting that governs it.
    assert "[config:stop_secs]" in lines[0]


def test_summary_reports_percentiles_and_worst_stage():
    call = CallTrace()
    call.add(turn(1.0))
    call.add(turn(2.0))

    text = "\n".join(summary(call))

    assert "2 turns" in text
    assert "p50" in text and "p95" in text
    assert "tts ttfb [tts]" in text


def test_summary_without_turns_says_so():
    assert "No turns measured" in summary(CallTrace())[0]


def test_summary_counts_interruptions():
    call = CallTrace()
    call.add(turn(1.0, interrupted=True))
    call.add(turn(1.0))

    assert "1 of 2 turns were interrupted" in "\n".join(summary(call))
