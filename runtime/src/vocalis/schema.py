"""The agent config JSON Schema, and schema errors translated into node-level issues.

Everything here is read from schema/agent.v1.schema.json: node types come from the
`Node` oneOf, port types from each node definition's `x-ports`.
"""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from vocalis.issues import Issue
from vocalis.paths import schema_dir

AGENT_SCHEMA_FILE = "agent.v1.schema.json"
PROVIDER_SCHEMA_FILE = "provider.v1.schema.json"


@dataclass(frozen=True)
class Ports:
    input: str
    output: str


@cache
def agent_schema() -> dict[str, Any]:
    return json.loads((schema_dir() / AGENT_SCHEMA_FILE).read_text())


@cache
def provider_schema() -> dict[str, Any]:
    return json.loads((schema_dir() / PROVIDER_SCHEMA_FILE).read_text())


@cache
def _node_def_names() -> dict[str, str]:
    """Node type -> name of its $defs entry, e.g. {"llm": "LlmNode"}."""
    defs = agent_schema()["$defs"]
    names = [ref["$ref"].rsplit("/", 1)[1] for ref in defs["Node"]["oneOf"]]
    return {defs[name]["properties"]["type"]["const"]: name for name in names}


def node_types() -> list[str]:
    return list(_node_def_names())


@cache
def node_ports() -> dict[str, Ports]:
    defs = agent_schema()["$defs"]
    return {t: Ports(**defs[name]["x-ports"]) for t, name in _node_def_names().items()}


@cache
def _validator(def_name: str | None = None) -> Draft202012Validator:
    schema = agent_schema()
    if def_name is not None:
        schema = {"$defs": schema["$defs"], "$ref": f"#/$defs/{def_name}"}
    return Draft202012Validator(schema)


def schema_issues(data: Any) -> list[Issue]:
    """Validate a raw config against the agent schema.

    A bad node fails the `Node` oneOf as a whole, which jsonschema reports as "not
    valid under any of the given schemas". To say what is actually wrong, each
    failing node is re-validated against the definition for its own `type`.
    """
    issues: list[Issue] = []
    bad_nodes: set[int] = set()

    for error in _validator().iter_errors(data):
        path = list(error.absolute_path)
        if len(path) >= 2 and path[0] == "nodes":
            bad_nodes.add(path[1])
        elif len(path) >= 2 and path[0] == "edges":
            issues.append(Issue(describe(error, path[2:]), edge_index=path[1], path=pointer(path)))
        else:
            issues.append(Issue(describe(error, path), path=pointer(path)))

    for index in sorted(bad_nodes):
        issues.extend(_node_issues(index, data["nodes"][index]))
    return issues


def _node_issues(index: int, node: Any) -> list[Issue]:
    base = ["nodes", index]
    if not isinstance(node, dict):
        return [Issue("each node must be an object", node_index=index, path=pointer(base))]

    node_id = node.get("id") if isinstance(node.get("id"), str) else None
    node_type = node.get("type")
    if node_type not in _node_def_names():
        message = (
            f"type must be one of {', '.join(node_types())} (got {node_type!r})"
            if "type" in node
            else 'missing required field "type"'
        )
        return [Issue(message, node_id=node_id, node_index=index, path=pointer([*base, "type"]))]

    return [
        Issue(
            describe(error, list(error.absolute_path)),
            node_id=node_id,
            node_index=index,
            path=pointer([*base, *error.absolute_path]),
        )
        for error in _validator(_node_def_names()[node_type]).iter_errors(node)
    ]


_REQUIRED = re.compile(r"^'(.+)' is a required property$")


def describe(error: ValidationError, field: Sequence[str | int] = ()) -> str:
    """Human-readable message for a schema error, prefixed with the offending field."""
    if error.validator == "required" and (match := _REQUIRED.match(error.message)):
        message = f'missing required field "{match.group(1)}"'
    elif error.validator == "additionalProperties" and isinstance(error.instance, dict):
        allowed = error.schema.get("properties", {})
        unknown = ", ".join(f'"{key}"' for key in error.instance if key not in allowed)
        message = f"unknown field {unknown}"
    else:
        message = error.message

    return f"{dotted(field)}: {message}" if field else message


def dotted(path: Sequence[str | int]) -> str:
    """["params", "voices", 0] -> "params.voices[0]"."""
    out = ""
    for part in path:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out


def pointer(path: Sequence[str | int]) -> str:
    """JSON pointer (RFC 6901) for a path, e.g. "/nodes/2/params"."""
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in path)
