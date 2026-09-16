"""Agent config model and loading.

The JSON Schema is the contract; these dataclasses are just a typed view of a config
that has already passed it. A test keeps their fields in sync with the schema.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vocalis.issues import ConfigError, Issue
from vocalis.schema import schema_issues


@dataclass(frozen=True)
class Node:
    id: str
    type: str
    provider: str
    params: dict[str, Any] = field(default_factory=dict)
    label: str | None = None
    system_prompt: str | None = None


@dataclass(frozen=True)
class Edge:
    source: str
    target: str


@dataclass(frozen=True)
class AgentConfig:
    schema_version: int
    name: str
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    description: str | None = None

    def node(self, node_id: str) -> Node:
        return next(node for node in self.nodes if node.id == node_id)


def parse_config(data: Any, source: str | None = None) -> AgentConfig:
    """Validate a decoded config against the schema and return the typed model."""
    issues = schema_issues(data)
    if issues:
        raise ConfigError(issues, source)

    return AgentConfig(
        schema_version=data["schema_version"],
        name=data["name"],
        description=data.get("description"),
        nodes=tuple(
            Node(**{**node, "params": dict(node.get("params", {}))}) for node in data["nodes"]
        ),
        edges=tuple(Edge(**edge) for edge in data["edges"]),
    )


def load_config(path: str | Path) -> AgentConfig:
    """Read and validate an agent config file."""
    path = Path(path)
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        issue = Issue(f"not valid JSON: {e.msg} (line {e.lineno}, column {e.colno})")
        raise ConfigError([issue], str(path)) from e
    return parse_config(data, str(path))
