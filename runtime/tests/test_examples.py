"""Every shipped example compiles against the real provider plugins."""

import pytest

from helpers import REPO_ROOT
from vocalis import ProviderRegistry, compile_agent, load_config, validate

EXAMPLES = sorted((REPO_ROOT / "examples").glob("*.json"))


@pytest.fixture(scope="module")
def registry() -> ProviderRegistry:
    return ProviderRegistry.from_directory()


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_validates(path, registry):
    assert validate(load_config(path), registry) == []


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_compiles_with_secrets_set(path, registry):
    config = load_config(path)
    env = {name: "test" for spec in registry for name in spec.env}

    agent = compile_agent(config, registry, env)

    assert [c.node.id for c in agent.nodes] == [edge.source for edge in config.edges] + [
        config.edges[-1].target
    ]
