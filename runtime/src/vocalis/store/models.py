"""Tables for saved agents and their version history.

An agent's current config is simply its highest-numbered version: versions are never
updated or deleted, so the history is a faithful record. Restoring an old version
writes a new version with that config rather than rewinding.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["AgentVersion"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        order_by="AgentVersion.version",
    )


class AgentVersion(Base):
    __tablename__ = "agent_versions"
    __table_args__ = (
        UniqueConstraint("agent_id", "version", name="uq_agent_versions_agent_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    config: Mapped[dict] = mapped_column(JSONB)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agent: Mapped[Agent] = relationship(back_populates="versions")


class CallRecord(Base):
    """One call that happened, kept so its latency can be compared with the next one."""

    __tablename__ = "calls"

    # The id comes from the live call, which the browser also uses in URLs, so it's
    # a short opaque string rather than a UUID.
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100))
    agent_slug: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    agent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # The config exactly as it ran: an agent can be edited between calls, and a
    # comparison is meaningless without knowing what each call actually used.
    config: Mapped[dict] = mapped_column(JSONB)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    interrupted_turns: Mapped[int] = mapped_column(Integer, default=0)
    p50_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    p95_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    turns: Mapped[list["CallTurn"]] = relationship(
        back_populates="call", cascade="all, delete-orphan", order_by="CallTurn.turn"
    )
    messages: Mapped[list["CallMessage"]] = relationship(
        back_populates="call", cascade="all, delete-orphan", order_by="CallMessage.at"
    )


class CallTurn(Base):
    """What one turn of a call cost, stage by stage."""

    __tablename__ = "call_turns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    call_id: Mapped[str] = mapped_column(ForeignKey("calls.id", ondelete="CASCADE"), index=True)
    turn: Mapped[int] = mapped_column(Integer)
    total_ms: Mapped[int] = mapped_column(Integer)
    interrupted: Mapped[bool] = mapped_column(Boolean, default=False)
    stages: Mapped[list] = mapped_column(JSONB)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    call: Mapped[CallRecord] = relationship(back_populates="turns")


class CallMessage(Base):
    """A line of the conversation."""

    __tablename__ = "call_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    call_id: Mapped[str] = mapped_column(ForeignKey("calls.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))
    text: Mapped[str] = mapped_column(Text)
    interrupted: Mapped[bool] = mapped_column(Boolean, default=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    call: Mapped[CallRecord] = relationship(back_populates="messages")
