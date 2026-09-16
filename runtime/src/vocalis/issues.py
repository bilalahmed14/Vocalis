"""Validation problems that point at the node or edge that caused them."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    """One problem with an agent config.

    `node_id` / `edge_index` let the canvas highlight the culprit (`node_index` covers
    nodes whose id is itself missing or invalid); `path` is a JSON pointer into the
    config (e.g. "/nodes/2/params/model").
    """

    message: str
    node_id: str | None = None
    node_index: int | None = None
    edge_index: int | None = None
    path: str = ""

    def __str__(self) -> str:
        if self.node_id is not None:
            where = f'node "{self.node_id}"'
        elif self.node_index is not None:
            where = f"node #{self.node_index}"
        elif self.edge_index is not None:
            where = f"edge {self.edge_index}"
        else:
            where = "config"
        return f"{where}: {self.message}"


class ConfigError(Exception):
    """Raised when an agent config can't be loaded or compiled."""

    def __init__(self, issues: Sequence[Issue], source: str | None = None):
        self.issues = list(issues)
        self.source = source
        super().__init__(str(self))

    def __str__(self) -> str:
        count = len(self.issues)
        header = f"invalid agent config ({count} problem{'s' if count != 1 else ''})"
        if self.source:
            header = f"{self.source}: {header}"
        return "\n".join([header, *(f"  - {issue}" for issue in self.issues)])
