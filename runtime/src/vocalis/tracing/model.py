"""What a traced call records.

A turn is the unit that matters for latency: the user stops speaking, and some time
later the agent starts. Every stage in between is named, and the stages add up to the
total, so nothing hides in the gaps between services.
"""

from dataclasses import dataclass, field
from statistics import median


@dataclass(frozen=True)
class Stage:
    """One named slice of a turn.

    `node_id` is set when the time belongs to a node on the canvas; it's None for
    time nobody owns, like the silence a VAD waits out.
    """

    key: str
    label: str
    owner: str
    secs: float
    node_id: str | None = None

    @property
    def ms(self) -> float:
        return self.secs * 1000


@dataclass(frozen=True)
class TurnTrace:
    """One user-to-agent cycle."""

    turn: int
    total_secs: float
    stages: tuple[Stage, ...] = ()
    transcript: str | None = None
    reply: str | None = None
    interrupted: bool = False

    @property
    def total_ms(self) -> float:
        return self.total_secs * 1000

    def by_node(self) -> dict[str, float]:
        """Seconds spent per node, for the badges on the canvas."""
        totals: dict[str, float] = {}
        for stage in self.stages:
            if stage.node_id:
                totals[stage.node_id] = totals.get(stage.node_id, 0) + stage.secs
        return totals


@dataclass
class CallTrace:
    """Every turn in one call, plus the summary you actually read."""

    turns: list[TurnTrace] = field(default_factory=list)

    def add(self, turn: TurnTrace) -> None:
        self.turns.append(turn)

    @property
    def totals_ms(self) -> list[float]:
        return [turn.total_ms for turn in self.turns]

    def percentile(self, fraction: float) -> float:
        """A rough percentile of turn latency; calls are too short for anything fancier."""
        if not self.turns:
            return 0.0
        ordered = sorted(self.totals_ms)
        index = min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
        return ordered[index]

    def slowest_stages(self, limit: int = 5) -> list[tuple[str, float]]:
        """Median cost of each stage across turns, worst first.

        Median rather than mean: one cold model load shouldn't decide where you spend
        your optimization effort.
        """
        samples: dict[str, list[float]] = {}
        for turn in self.turns:
            for stage in turn.stages:
                samples.setdefault(f"{stage.label} [{stage.node_id or stage.owner}]", []).append(
                    stage.ms
                )
        ranked = sorted(
            ((label, median(values)) for label, values in samples.items()),
            key=lambda pair: pair[1],
            reverse=True,
        )
        return ranked[:limit]
