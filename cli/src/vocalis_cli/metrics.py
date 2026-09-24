"""Printing latency traces in the terminal."""

from vocalis.tracing import CallTrace, TurnTrace

BAR_WIDTH = 28


def turn_line(turn: TurnTrace) -> str:
    """One line per turn: how long the agent took to start answering."""
    flag = "  [interrupted]" if turn.interrupted else ""
    return f"  turn {turn.turn}: {turn.total_ms:.0f} ms to first audio{flag}"


def waterfall(turn: TurnTrace) -> list[str]:
    """Where the turn's time went, longest bar first, in the order it happened."""
    if not turn.stages:
        return []
    longest = max(stage.ms for stage in turn.stages) or 1
    lines = []
    for stage in turn.stages:
        bar = "█" * max(1, round(stage.ms / longest * BAR_WIDTH))
        where = stage.node_id or stage.owner
        lines.append(f"    {stage.ms:6.0f} ms  {bar:<{BAR_WIDTH}}  {stage.label} [{where}]")
    return lines


def summary(call: CallTrace) -> list[str]:
    """What to read after hanging up."""
    if not call.turns:
        return ["No turns measured. Did the agent answer?"]

    lines = [
        "",
        f"{len(call.turns)} turns   "
        f"p50 {call.percentile(0.5):.0f} ms   "
        f"p95 {call.percentile(0.95):.0f} ms   "
        f"worst {max(call.totals_ms):.0f} ms",
        "",
        "  slowest stages (median across turns):",
    ]
    lines += [f"    {ms:6.0f} ms  {label}" for label, ms in call.slowest_stages()]
    interrupted = sum(1 for turn in call.turns if turn.interrupted)
    if interrupted:
        lines.append(f"\n  {interrupted} of {len(call.turns)} turns were interrupted.")
    return lines
