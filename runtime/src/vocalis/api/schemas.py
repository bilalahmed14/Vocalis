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
