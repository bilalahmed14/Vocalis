"""Writing calls down, so today's latency can be compared with tomorrow's.

Writes happen on a background task per call: a slow database must never hold up a
live conversation.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from vocalis.store.models import Agent, CallMessage, CallRecord, CallTurn
from vocalis.tracing import percentile


@dataclass(frozen=True)
class CallSummary:
    id: str
    agent_name: str
    agent_slug: str | None
    agent_version: int | None
    started_at: datetime
    ended_at: datetime | None
    turn_count: int
    interrupted_turns: int
    p50_ms: int | None
    p95_ms: int | None


@dataclass(frozen=True)
class Overview:
    """Headline numbers for the whole workspace."""

    agents: int
    calls: int
    turns: int
    p50_ms: int | None
    p95_ms: int | None
    interrupted_share: float
    daily: list[dict[str, Any]]
    slowest_stages: list[dict[str, Any]]
    recent: list["CallSummary"]


@dataclass(frozen=True)
class CallDetail:
    summary: CallSummary
    config: dict[str, Any]
    turns: list[dict[str, Any]]
    messages: list[dict[str, Any]]


class CallStore:
    """Reads and writes call logs."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._sessions = session_factory

    async def start(
        self,
        call_id: str,
        config: dict[str, Any],
        slug: str | None = None,
        version: int | None = None,
    ) -> None:
        async with self._sessions() as session, session.begin():
            agent_id = None
            if slug:
                agent_id = await session.scalar(select(Agent.id).where(Agent.slug == slug))
            session.add(
                CallRecord(
                    id=call_id,
                    agent_id=agent_id,
                    agent_name=config.get("name", "Untitled agent"),
                    agent_slug=slug,
                    agent_version=version,
                    config=config,
                )
            )

    async def add_turn(self, call_id: str, turn: dict[str, Any]) -> None:
        async with self._sessions() as session, session.begin():
            session.add(
                CallTurn(
                    call_id=call_id,
                    turn=turn["turn"],
                    total_ms=turn["total_ms"],
                    interrupted=turn["interrupted"],
                    stages=turn["stages"],
                )
            )

    async def add_message(self, call_id: str, message: dict[str, Any]) -> None:
        async with self._sessions() as session, session.begin():
            session.add(
                CallMessage(
                    call_id=call_id,
                    role=message["role"],
                    text=message["text"],
                    interrupted=bool(message.get("interrupted")),
                )
            )

    async def finish(self, call_id: str) -> None:
        """Close the call and store its summary, so lists don't recompute it."""
        async with self._sessions() as session, session.begin():
            call = await session.get(CallRecord, call_id, options=[selectinload(CallRecord.turns)])
            if call is None:
                return
            totals = sorted(turn.total_ms for turn in call.turns)
            call.ended_at = datetime.now(UTC)
            call.turn_count = len(totals)
            call.interrupted_turns = sum(1 for turn in call.turns if turn.interrupted)
            call.p50_ms = _as_int(percentile(totals, 0.5))
            call.p95_ms = _as_int(percentile(totals, 0.95))

    async def list(self, slug: str | None = None, limit: int = 50) -> list[CallSummary]:
        async with self._sessions() as session:
            query = select(CallRecord).order_by(CallRecord.started_at.desc()).limit(limit)
            if slug:
                query = query.where(CallRecord.agent_slug == slug)
            return [_summary(call) for call in (await session.scalars(query)).all()]

    async def get(self, call_id: str) -> CallDetail | None:
        async with self._sessions() as session:
            call = await session.get(
                CallRecord,
                call_id,
                options=[selectinload(CallRecord.turns), selectinload(CallRecord.messages)],
            )
            if call is None:
                return None
            return CallDetail(
                summary=_summary(call),
                config=call.config,
                turns=[
                    {
                        "turn": turn.turn,
                        "total_ms": turn.total_ms,
                        "interrupted": turn.interrupted,
                        "stages": turn.stages,
                        "at": turn.at.isoformat(),
                    }
                    for turn in call.turns
                ],
                messages=[
                    {
                        "role": message.role,
                        "text": message.text,
                        "interrupted": message.interrupted,
                        "at": message.at.isoformat(),
                    }
                    for message in call.messages
                ],
            )

    async def delete(self, call_id: str) -> bool:
        async with self._sessions() as session, session.begin():
            call = await session.get(CallRecord, call_id)
            if call is None:
                return False
            await session.delete(call)
            return True

    async def overview(self, days: int = 14, sample: int = 300) -> Overview:
        """Everything the home page shows, in one pass over recent calls.

        Aggregation happens in Python rather than SQL: the turn stages live in JSONB,
        and at this scale a few hundred rows is cheaper to read than to unnest.
        """
        since = datetime.now(UTC) - timedelta(days=days)

        async with self._sessions() as session:
            agents = await session.scalar(select(func.count(Agent.id))) or 0
            calls = (
                await session.scalars(
                    select(CallRecord)
                    .options(selectinload(CallRecord.turns))
                    .where(CallRecord.started_at >= since)
                    .order_by(CallRecord.started_at.desc())
                    .limit(sample)
                )
            ).all()

        turns = [turn for call in calls for turn in call.turns]
        totals = [turn.total_ms for turn in turns]
        interrupted = sum(1 for turn in turns if turn.interrupted)

        by_day: dict[str, list[int]] = {}
        calls_per_day: dict[str, int] = {}
        for call in calls:
            day = call.started_at.date().isoformat()
            calls_per_day[day] = calls_per_day.get(day, 0) + 1
            by_day.setdefault(day, []).extend(turn.total_ms for turn in call.turns)

        stage_samples: dict[tuple[str, str | None], list[int]] = {}
        for turn in turns:
            for stage in turn.stages:
                key = (stage.get("label", stage.get("key", "?")), stage.get("node_id"))
                stage_samples.setdefault(key, []).append(stage.get("ms", 0))

        slowest = sorted(
            (
                {"label": label, "node_id": node_id, "median_ms": int(median(values))}
                for (label, node_id), values in stage_samples.items()
            ),
            key=lambda stage: stage["median_ms"],
            reverse=True,
        )

        return Overview(
            agents=agents,
            calls=len(calls),
            turns=len(turns),
            p50_ms=_as_int(percentile(totals, 0.5)),
            p95_ms=_as_int(percentile(totals, 0.95)),
            interrupted_share=round(interrupted / len(turns), 3) if turns else 0.0,
            daily=[
                {
                    "day": day,
                    "calls": calls_per_day[day],
                    "p50_ms": _as_int(percentile(values, 0.5)),
                }
                for day, values in sorted(by_day.items())
            ],
            slowest_stages=slowest[:6],
            recent=[_summary(call) for call in calls[:8]],
        )

    async def stats(self, slug: str) -> dict[str, Any]:
        """Headline numbers for one agent, for the top of its calls tab."""
        async with self._sessions() as session:
            row = (
                await session.execute(
                    select(
                        func.count(CallRecord.id),
                        func.sum(CallRecord.turn_count),
                        func.avg(CallRecord.p50_ms),
                    ).where(CallRecord.agent_slug == slug)
                )
            ).one()
            return {
                "calls": row[0] or 0,
                "turns": int(row[1] or 0),
                "median_ms": int(row[2]) if row[2] is not None else None,
            }


class CallRecorder:
    """Queues a call's writes so the pipeline never waits on the database."""

    def __init__(self, store: CallStore, call_id: str):
        self._store = store
        self._call_id = call_id
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker = asyncio.create_task(self._drain())

    def record(self, event: dict[str, Any]) -> None:
        self._queue.put_nowait(event)

    async def close(self) -> None:
        await self._queue.join()
        self._worker.cancel()
        try:
            await self._store.finish(self._call_id)
        except Exception:  # pragma: no cover - a log shouldn't break a call
            logger.exception("could not finish call {}", self._call_id)

    async def _drain(self) -> None:
        while True:
            event = await self._queue.get()
            try:
                if event["type"] == "turn":
                    await self._store.add_turn(self._call_id, event)
                elif event["type"] == "transcript":
                    await self._store.add_message(self._call_id, event)
            except Exception:  # pragma: no cover - a log shouldn't break a call
                logger.exception("could not record {} for call {}", event["type"], self._call_id)
            finally:
                self._queue.task_done()


def _as_int(value: float | None) -> int | None:
    return None if value is None else int(value)


def _summary(call: CallRecord) -> CallSummary:
    return CallSummary(
        id=call.id,
        agent_name=call.agent_name,
        agent_slug=call.agent_slug,
        agent_version=call.agent_version,
        started_at=call.started_at,
        ended_at=call.ended_at,
        turn_count=call.turn_count,
        interrupted_turns=call.interrupted_turns,
        p50_ms=call.p50_ms,
        p95_ms=call.p95_ms,
    )
