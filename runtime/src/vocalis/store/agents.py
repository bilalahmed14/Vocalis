"""Saving, listing and versioning agents.

This layer only persists: configs are validated by the API before they reach it, so
a stored version is always one the compiler accepted.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from vocalis.store.models import Agent, AgentVersion


class AgentNotFound(LookupError):
    """No agent (or version) with that name."""


@dataclass(frozen=True)
class VersionSummary:
    version: int
    note: str | None
    created_at: datetime


@dataclass(frozen=True)
class AgentSummary:
    name: str
    slug: str
    version: int
    updated_at: datetime


@dataclass(frozen=True)
class SavedAgent:
    name: str
    slug: str
    version: int
    config: dict[str, Any]
    updated_at: datetime


class AgentStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._sessions = session_factory

    async def list_agents(self) -> list[AgentSummary]:
        async with self._sessions() as session:
            agents = (
                await session.scalars(
                    select(Agent).options(selectinload(Agent.versions)).order_by(Agent.name)
                )
            ).all()
            return [
                AgentSummary(
                    name=agent.name,
                    slug=agent.slug,
                    version=agent.versions[-1].version if agent.versions else 0,
                    updated_at=agent.updated_at,
                )
                for agent in agents
            ]

    async def create(self, config: dict[str, Any], note: str | None = None) -> SavedAgent:
        async with self._sessions() as session, session.begin():
            slug = await self._free_slug(session, slugify(config["name"]))
            agent = Agent(name=config["name"], slug=slug)
            agent.versions.append(AgentVersion(version=1, config=config, note=note))
            session.add(agent)
            await session.flush()
            return _saved(agent, agent.versions[-1])

    async def get(self, slug: str) -> SavedAgent:
        async with self._sessions() as session:
            agent = await self._agent(session, slug)
            if not agent.versions:
                raise AgentNotFound(f'agent "{slug}" has no versions')
            return _saved(agent, agent.versions[-1])

    async def save(self, slug: str, config: dict[str, Any], note: str | None = None) -> SavedAgent:
        """Write the config as the agent's next version."""
        async with self._sessions() as session, session.begin():
            agent = await self._agent(session, slug)
            agent.name = config["name"]
            version = AgentVersion(
                version=(agent.versions[-1].version if agent.versions else 0) + 1,
                config=config,
                note=note,
            )
            agent.versions.append(version)
            await session.flush()
            # Postgres writes updated_at, so load it back before the session closes.
            await session.refresh(agent, ["updated_at"])
            return _saved(agent, version)

    async def versions(self, slug: str) -> list[VersionSummary]:
        async with self._sessions() as session:
            agent = await self._agent(session, slug)
            return [
                VersionSummary(version=v.version, note=v.note, created_at=v.created_at)
                for v in reversed(agent.versions)
            ]

    async def version(self, slug: str, version: int) -> SavedAgent:
        async with self._sessions() as session:
            agent = await self._agent(session, slug)
            found = next((v for v in agent.versions if v.version == version), None)
            if found is None:
                raise AgentNotFound(f'agent "{slug}" has no version {version}')
            return _saved(agent, found)

    async def restore(self, slug: str, version: int) -> SavedAgent:
        """Copy an old version forward, so the history keeps every step."""
        old = await self.version(slug, version)
        return await self.save(slug, old.config, note=f"restored version {version}")

    async def delete(self, slug: str) -> None:
        async with self._sessions() as session, session.begin():
            await session.delete(await self._agent(session, slug))

    async def _agent(self, session: AsyncSession, slug: str) -> Agent:
        agent = await session.scalar(
            select(Agent).options(selectinload(Agent.versions)).where(Agent.slug == slug)
        )
        if agent is None:
            raise AgentNotFound(f'no agent called "{slug}"')
        return agent

    async def _free_slug(self, session: AsyncSession, wanted: str) -> str:
        taken = set(
            (await session.scalars(select(Agent.slug).where(Agent.slug.like(f"{wanted}%")))).all()
        )
        if wanted not in taken:
            return wanted
        for suffix in range(2, len(taken) + 3):
            if (candidate := f"{wanted}-{suffix}") not in taken:
                return candidate
        raise RuntimeError("unreachable")  # pragma: no cover


def _saved(agent: Agent, version: AgentVersion) -> SavedAgent:
    return SavedAgent(
        name=agent.name,
        slug=agent.slug,
        version=version.version,
        config=version.config,
        updated_at=agent.updated_at,
    )


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]
    return slug or "agent"
