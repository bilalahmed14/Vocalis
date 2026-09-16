"""Shared test data and helpers for runtime tests."""

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

PASSTHROUGH_ADAPTER = """
from pipecat.processors.frame_processor import FrameProcessor


class Recorder(FrameProcessor):
    def __init__(self, params, ctx):
        super().__init__(name=ctx.node.id)
        self.params = params
        self.ctx = ctx


def create(params, ctx):
    return Recorder(params, ctx)
"""

VALID_CONFIG: dict[str, Any] = {
    "schema_version": 1,
    "name": "Test agent",
    "nodes": [
        {"id": "vad", "type": "vad", "provider": "fake", "params": {}},
        {"id": "stt", "type": "stt", "provider": "fake", "params": {"model": "small"}},
        {
            "id": "llm",
            "type": "llm",
            "provider": "fake",
            "system_prompt": "Be brief.",
            "params": {},
        },
        {"id": "tts", "type": "tts", "provider": "fake", "params": {}},
    ],
    "edges": [
        {"source": "vad", "target": "stt"},
        {"source": "stt", "target": "llm"},
        {"source": "llm", "target": "tts"},
    ],
}


def write_provider(
    root: Path,
    node_type: str,
    provider_id: str,
    *,
    params: dict[str, Any] | None = None,
    env: list[str] | None = None,
    adapter: str | None = PASSTHROUGH_ADAPTER,
    manifest: dict[str, Any] | None = None,
) -> Path:
    """Create a provider plugin folder under `root` and return it."""
    folder = root / node_type / provider_id
    folder.mkdir(parents=True)
    if manifest is None:
        manifest = {
            "id": provider_id,
            "type": node_type,
            "name": provider_id.title(),
            "env": env or [],
            "params": params or {"type": "object"},
        }
    (folder / "provider.json").write_text(json.dumps(manifest))
    if adapter is not None:
        (folder / "adapter.py").write_text(adapter)
    return folder
