"""Locations of the shared schema and provider directories.

Both live at the repo root so the runtime, dashboard and CLI read the same files.
Override them with VOCALIS_SCHEMA_DIR / VOCALIS_PROVIDERS_DIR (e.g. in a container).
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def schema_dir() -> Path:
    return Path(os.environ.get("VOCALIS_SCHEMA_DIR", REPO_ROOT / "schema"))


def providers_dir() -> Path:
    return Path(os.environ.get("VOCALIS_PROVIDERS_DIR", REPO_ROOT / "providers"))
