"""Fixtures for provider adapter tests.

Adapters are built exactly as the compiler builds them (params validated, defaults
applied), with fake secrets. Constructing a Pipecat service doesn't open any
connection, so these tests run offline.
"""

from collections.abc import Callable
from typing import Any

import pytest
from pipecat.processors.frame_processor import FrameProcessor

from vocalis import BuildContext, Node, ProviderRegistry


@pytest.fixture(scope="session")
def registry() -> ProviderRegistry:
    return ProviderRegistry.from_directory()


@pytest.fixture
def build(registry) -> Callable[..., FrameProcessor]:
    def _build(
        node_type: str,
        provider: str,
        params: dict[str, Any] | None = None,
        system_prompt: str | None = None,
    ) -> FrameProcessor:
        spec = registry.get(node_type, provider)
        assert spec is not None, f"no {node_type} provider {provider!r}"
        params = params or {}
        errors = [e.message for e in spec.params_validator.iter_errors(params)]
        assert errors == [], errors

        node = Node(
            id=node_type,
            type=node_type,
            provider=provider,
            params=params,
            system_prompt=system_prompt,
        )
        env = {name: f"test-{name.lower()}" for name in spec.env}
        return spec.load_adapter()(spec.with_defaults(params), BuildContext(node=node, env=env))

    return _build
