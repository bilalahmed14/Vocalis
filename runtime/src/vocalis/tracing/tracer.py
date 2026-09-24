"""Turn-by-turn latency tracing for a running agent.

Pipecat measures where a turn's time goes; what it can't know is which node on the
canvas each measurement belongs to. The tracer bridges the two: it maps every
contribution back to a node id, so "0.4s in tts" becomes "0.4s in the node you can
click on", and keeps the turns for a summary at the end of the call.
"""

from collections.abc import Callable

from pipecat.observers.base_observer import BaseObserver
from pipecat.observers.turn_tracking_observer import TurnTrackingObserver
from pipecat.observers.user_bot_latency_observer import (
    LatencyBreakdown,
    LatencyOwnerKind,
    UserBotLatencyObserver,
)

from vocalis.compiler import CompiledAgent
from vocalis.tracing.model import CallTrace, Stage, TurnTrace


class CallTracer:
    """Collects a `CallTrace` from a running pipeline.

    Pass `tracer.observers` to the pipeline worker, and read `tracer.call` after (or
    during) the call. `on_turn` fires as each turn completes, which is what the CLI
    prints and what the dashboard will stream.
    """

    def __init__(self, agent: CompiledAgent, on_turn: Callable[[TurnTrace], None] | None = None):
        self._nodes = {compiled.processor.name: compiled.node.id for compiled in agent.nodes}
        self._on_turn = on_turn
        self.call = CallTrace()

        self._latency = UserBotLatencyObserver()
        self._turns = TurnTrackingObserver()
        self._interrupted: dict[int, bool] = {}
        self._turn_number = 0

        @self._turns.event_handler("on_turn_started")
        async def on_turn_started(observer, turn: int):
            self._turn_number = turn

        @self._turns.event_handler("on_turn_ended")
        async def on_turn_ended(observer, turn: int, duration: float, was_interrupted: bool):
            self._interrupted[turn] = was_interrupted

        @self._latency.event_handler("on_latency_breakdown")
        async def on_latency_breakdown(observer, breakdown: LatencyBreakdown):
            self._record(breakdown)

    @property
    def observers(self) -> list[BaseObserver]:
        return [self._latency, self._turns]

    def _record(self, breakdown: LatencyBreakdown) -> None:
        stages = tuple(
            Stage(
                key=contribution.key,
                label=contribution.label,
                owner=contribution.owner,
                secs=contribution.duration_secs,
                node_id=self._node_for(contribution.owner, contribution.owner_kind),
            )
            for contribution in breakdown.contributions
        )
        turn = TurnTrace(
            turn=self._turn_number,
            total_secs=sum(stage.secs for stage in stages),
            stages=stages,
            interrupted=self._interrupted.get(self._turn_number, False),
        )
        self.call.add(turn)
        if self._on_turn:
            self._on_turn(turn)

    def _node_for(self, owner: str, kind: LatencyOwnerKind) -> str | None:
        """Which node a contribution belongs to, if any.

        Owners are processor names for services ("DeepgramTTSService#0") and `config:`
        tags for settings, which belong to no single node.
        """
        if kind is not LatencyOwnerKind.SERVICE:
            return None
        return self._nodes.get(owner)
