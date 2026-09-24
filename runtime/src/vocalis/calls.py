"""Browser calls: a WebRTC session running one agent, with its transcript and timings.

A call owns a Pipecat pipeline, a tracer, and a list of subscribers. Anything worth
watching — the transcript as it happens, each turn's latency — is published to those
subscribers as it occurs, so the dashboard can show a call while it's still going.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from loguru import logger
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.request_handler import (
    SmallWebRTCRequest,
    SmallWebRTCRequestHandler,
)
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.workers.runner import WorkerRunner

from vocalis.compiler import compile_agent
from vocalis.config import AgentConfig
from vocalis.providers import ProviderRegistry
from vocalis.tracing import CallTracer, TurnTrace

CallState = Literal["connecting", "live", "ended"]


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Call:
    """One live call, and everything the dashboard wants to know about it."""

    id: str
    agent_name: str
    slug: str | None
    tracer: CallTracer
    state: CallState = "connecting"
    transcript: list[dict[str, Any]] = field(default_factory=list)
    turns: list[dict[str, Any]] = field(default_factory=list)
    _subscribers: list[asyncio.Queue] = field(default_factory=list)
    _task: asyncio.Task | None = None

    def publish(self, event: dict[str, Any]) -> None:
        """Send an event to every watcher. Never blocks the pipeline."""
        event = {**event, "at": _now()}
        if event["type"] == "transcript":
            self.transcript.append(event)
        elif event["type"] == "turn":
            self.turns.append(event)
        for queue in self._subscribers:
            queue.put_nowait(event)

    async def watch(self) -> AsyncIterator[dict[str, Any]]:
        """Replay what has happened so far, then follow along live."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            yield {"type": "state", "state": self.state, "at": _now()}
            for event in [*self.transcript, *self.turns]:
                yield event
            while True:
                event = await queue.get()
                yield event
                if event["type"] == "state" and event["state"] == "ended":
                    return
        finally:
            self._subscribers.remove(queue)

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "slug": self.slug,
            "state": self.state,
            "turns": len(self.turns),
        }


class CallManager:
    """Starts calls, keeps the live ones, and cleans up after them."""

    def __init__(self, registry: ProviderRegistry | None = None):
        self._registry = registry
        self._calls: dict[str, Call] = {}
        self._handler = SmallWebRTCRequestHandler()

    @property
    def calls(self) -> list[Call]:
        return list(self._calls.values())

    def get(self, call_id: str) -> Call | None:
        return self._calls.get(call_id)

    async def start(
        self, config: AgentConfig, request: SmallWebRTCRequest, slug: str | None = None
    ) -> dict[str, Any]:
        """Answer a browser's offer and run the agent for as long as the call lasts.

        The agent is compiled before the answer goes out, so a config that can't run
        fails here rather than after the caller hears silence.
        """
        agent = compile_agent(config, self._registry)

        async def on_connection(connection: SmallWebRTCConnection) -> None:
            call = self._create(connection.pc_id, config, agent, slug)
            call._task = asyncio.create_task(self._run(call, connection, agent))

        answer = await self._handler.handle_web_request(on_connection, request)
        return answer or {}

    def _create(self, call_id: str, config: AgentConfig, agent, slug: str | None) -> Call:
        call = Call(
            id=call_id,
            agent_name=config.name,
            slug=slug,
            tracer=CallTracer(agent, on_turn=lambda turn: self._on_turn(call_id, turn)),
        )
        self._calls[call_id] = call
        return call

    def _on_turn(self, call_id: str, turn: TurnTrace) -> None:
        call = self._calls.get(call_id)
        if not call:
            return
        call.publish(
            {
                "type": "turn",
                "turn": turn.turn,
                "total_ms": round(turn.total_ms),
                "interrupted": turn.interrupted,
                "by_node": {node: round(secs * 1000) for node, secs in turn.by_node().items()},
                "stages": [
                    {
                        "key": stage.key,
                        "label": stage.label,
                        "owner": stage.owner,
                        "node_id": stage.node_id,
                        "ms": round(stage.ms),
                    }
                    for stage in turn.stages
                ],
            }
        )

    async def _run(self, call: Call, connection: SmallWebRTCConnection, agent) -> None:
        transport = SmallWebRTCTransport(
            webrtc_connection=connection,
            params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
        )

        user = agent.context_aggregator.user()
        assistant = agent.context_aggregator.assistant()

        @user.event_handler("on_user_turn_stopped")
        async def on_user_turn_stopped(aggregator, strategy, message):
            if message.content:
                call.publish({"type": "transcript", "role": "user", "text": message.content})

        @assistant.event_handler("on_assistant_turn_stopped")
        async def on_assistant_turn_stopped(aggregator, message):
            if message.content:
                call.publish(
                    {
                        "type": "transcript",
                        "role": "agent",
                        "text": message.content,
                        "interrupted": message.interrupted,
                    }
                )

        worker = PipelineWorker(
            agent.pipeline(transport),
            params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
            observers=call.tracer.observers,
        )

        call.state = "live"
        call.publish({"type": "state", "state": "live"})
        try:
            await WorkerRunner(handle_sigint=False).run(worker)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # pragma: no cover - depends on the network
            logger.exception("call {} failed", call.id)
            call.publish({"type": "error", "message": str(e)})
        finally:
            call.state = "ended"
            call.publish({"type": "state", "state": "ended"})
            self._calls.pop(call.id, None)

    async def hangup(self, call_id: str) -> bool:
        call = self._calls.get(call_id)
        if not call:
            return False
        if call._task:
            call._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await call._task
        call.state = "ended"
        call.publish({"type": "state", "state": "ended"})
        self._calls.pop(call_id, None)
        return True

    async def shutdown(self) -> None:
        for call_id in list(self._calls):
            await self.hangup(call_id)
