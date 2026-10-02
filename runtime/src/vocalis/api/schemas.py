"""Request and response shapes for the HTTP API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from vocalis.issues import Issue


class IssueOut(BaseModel):
    """A problem, pointing at the node or edge that caused it."""

    message: str
    node_id: str | None = None
    node_index: int | None = None
    edge_index: int | None = None
    path: str = ""

    @classmethod
    def of(cls, issue: Issue) -> "IssueOut":
        return cls(
            message=str(issue),
            node_id=issue.node_id,
            node_index=issue.node_index,
            edge_index=issue.edge_index,
            path=issue.path,
        )


class ValidationOut(BaseModel):
    valid: bool
    issues: list[IssueOut] = []


class ConfigIn(BaseModel):
    config: dict[str, Any]
    note: str | None = Field(default=None, max_length=200)


class AgentOut(BaseModel):
    name: str
    slug: str
    version: int
    config: dict[str, Any]
    updated_at: datetime


class AgentSummaryOut(BaseModel):
    name: str
    slug: str
    version: int
    updated_at: datetime


class VersionOut(BaseModel):
    version: int
    note: str | None
    created_at: datetime


class ProviderOut(BaseModel):
    id: str
    type: str
    name: str
    description: str = ""
    docs_url: str | None = None
    env: list[str] = []
    needs_vad: bool = False
    params: dict[str, Any]
    icon: str | None = None


class CallIn(BaseModel):
    """A browser's WebRTC offer, plus which agent should answer it."""

    sdp: str
    type: str
    pc_id: str | None = None
    restart_pc: bool | None = None
    slug: str | None = None
    config: dict[str, Any] | None = None


class CallOut(BaseModel):
    """The answer the browser needs to complete the connection."""

    sdp: str
    type: str
    pc_id: str
    call_id: str


class CallSummaryOut(BaseModel):
    id: str
    pc_id: str
    agent_name: str
    slug: str | None
    state: str
    turns: int


class CallLogOut(BaseModel):
    """One call that happened."""

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


class CallLogDetailOut(BaseModel):
    call: CallLogOut
    config: dict[str, Any]
    turns: list[dict[str, Any]]
    messages: list[dict[str, Any]]


class AgentCallStatsOut(BaseModel):
    calls: int
    turns: int
    median_ms: int | None


class TemplateOut(BaseModel):
    """A starting point for a new agent."""

    id: str
    name: str
    description: str = ""
    needs_keys: list[str] = []
    config: dict[str, Any]


class OverviewOut(BaseModel):
    """The home page: how the workspace has been behaving lately."""

    agents: int
    calls: int
    turns: int
    p50_ms: int | None
    p95_ms: int | None
    interrupted_share: float
    daily: list[dict[str, Any]]
    slowest_stages: list[dict[str, Any]]
    recent: list[CallLogOut]
