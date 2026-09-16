"""Provider plugins: discovery, param validation and adapter loading.

A plugin is a folder `providers/<type>/<id>/` containing:

    provider.json   manifest (schema/provider.v1.schema.json), incl. the params schema
    adapter.py      defines `create(params, ctx) -> FrameProcessor`
    icon.svg        optional, shown on the canvas

Manifests are read eagerly; adapters are imported only when a node is built, so
validating a config never pulls in heavy provider SDKs.
"""

import copy
import importlib.util
import json
import sys
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Protocol

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.transcriptions.language import Language

from vocalis.config import Node
from vocalis.paths import providers_dir
from vocalis.schema import describe, provider_schema


class ProviderError(Exception):
    """A provider plugin itself is broken (bad manifest, missing adapter)."""


@dataclass(frozen=True)
class BuildContext:
    """What an adapter gets besides its params."""

    node: Node
    env: Mapping[str, str]

    def secret(self, name: str) -> str:
        """Read an env var listed in the manifest; the compiler has checked it is set."""
        return self.env[name]


class Adapter(Protocol):
    def __call__(self, params: dict[str, Any], ctx: BuildContext) -> FrameProcessor: ...


def language(code: str) -> Language | str:
    """Turn a language param into what Pipecat services expect.

    Known codes ("en", "en-US") become `Language` values, which each service maps to
    its own format; anything else (e.g. Deepgram's "multi") is passed through as-is.
    """
    try:
        return Language(code)
    except ValueError:
        return code


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    type: str
    name: str
    path: Path
    params_schema: Mapping[str, Any]
    env: tuple[str, ...] = ()
    requires: Mapping[str, str] | None = None
    needs_vad: bool = False
    description: str = ""
    docs_url: str | None = None

    @cached_property
    def params_validator(self) -> Draft202012Validator:
        return Draft202012Validator(self.params_schema)

    def with_defaults(self, params: Mapping[str, Any]) -> dict[str, Any]:
        """Params with top-level defaults from the params schema filled in."""
        properties = self.params_schema.get("properties", {})
        defaults = {k: copy.deepcopy(v["default"]) for k, v in properties.items() if "default" in v}
        return {**defaults, **params}

    def missing_env(self, env: Mapping[str, str]) -> list[str]:
        return [name for name in self.env if not env.get(name)]

    def install_hint(self) -> str | None:
        """The command to install this provider's optional dependency, if it's missing."""
        if not self.requires or importlib.util.find_spec(self.requires["module"]) is not None:
            return None
        return f"uv sync --extra {self.requires['extra']}"

    def load_adapter(self) -> Adapter:
        file = self.path / "adapter.py"
        module_name = f"vocalis_providers.{self.type}.{self.id}"
        module = sys.modules.get(module_name)
        if module is None or getattr(module, "__file__", None) != str(file):
            spec = importlib.util.spec_from_file_location(module_name, file)
            if spec is None or spec.loader is None:
                raise ProviderError(f"{self.path}: cannot import adapter.py")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
            except BaseException:
                del sys.modules[module_name]
                raise

        create = getattr(module, "create", None)
        if not callable(create):
            raise ProviderError(f"{file}: missing create(params, ctx)")
        return create


class ProviderRegistry:
    """All installed provider plugins, keyed by (node type, provider id)."""

    def __init__(self, specs: Iterable[ProviderSpec] = ()):
        self._specs: dict[tuple[str, str], ProviderSpec] = {}
        for spec in specs:
            key = (spec.type, spec.id)
            if key in self._specs:
                raise ProviderError(f"duplicate {spec.type} provider {spec.id!r}")
            self._specs[key] = spec

    @classmethod
    def from_directory(cls, root: Path | None = None) -> "ProviderRegistry":
        root = providers_dir() if root is None else root
        return cls(_load_spec(path) for path in sorted(root.glob("*/*/provider.json")))

    def get(self, node_type: str, provider_id: str) -> ProviderSpec | None:
        return self._specs.get((node_type, provider_id))

    def for_type(self, node_type: str) -> list[ProviderSpec]:
        return [spec for (t, _), spec in self._specs.items() if t == node_type]

    def __iter__(self) -> Iterator[ProviderSpec]:
        return iter(self._specs.values())

    def __len__(self) -> int:
        return len(self._specs)


def _load_spec(manifest_path: Path) -> ProviderSpec:
    folder = manifest_path.parent
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        raise ProviderError(f"{manifest_path}: not valid JSON: {e}") from e

    errors = list(Draft202012Validator(provider_schema()).iter_errors(manifest))
    if errors:
        details = "; ".join(describe(e, list(e.absolute_path)) for e in errors)
        raise ProviderError(f"{manifest_path}: {details}")

    if (manifest["type"], manifest["id"]) != (folder.parent.name, folder.name):
        raise ProviderError(
            f"{manifest_path}: expected to live in providers/{manifest['type']}/{manifest['id']}/"
        )
    if not (folder / "adapter.py").is_file():
        raise ProviderError(f"{folder}: missing adapter.py")
    try:
        Draft202012Validator.check_schema(manifest["params"])
    except SchemaError as e:
        raise ProviderError(
            f"{manifest_path}: params is not a valid JSON Schema: {e.message}"
        ) from e

    return ProviderSpec(
        id=manifest["id"],
        type=manifest["type"],
        name=manifest["name"],
        path=folder,
        params_schema=manifest["params"],
        env=tuple(manifest.get("env", [])),
        requires=manifest.get("requires"),
        needs_vad=manifest.get("needs_vad", False),
        description=manifest.get("description", ""),
        docs_url=manifest.get("docs_url"),
    )
