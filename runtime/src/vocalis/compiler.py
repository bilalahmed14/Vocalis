"""Compile an agent config into a Pipecat pipeline.

    config ──validate──> ordered chain ──adapters──> processors ──> Pipeline

The compiler is transport-agnostic: `CompiledAgent.pipeline(transport)` wires the
same processors between a local mic/speaker (CLI) or a WebRTC call (dashboard).
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass

from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.transports.base_transport import BaseTransport

from vocalis.config import AgentConfig, Node
from vocalis.graph import order_chain
from vocalis.issues import ConfigError, Issue
from vocalis.providers import BuildContext, ProviderRegistry
from vocalis.schema import describe, pointer


@dataclass(frozen=True)
class CompiledNode:
    node: Node
    processor: FrameProcessor


@dataclass(frozen=True)
class CompiledAgent:
    config: AgentConfig
    nodes: tuple[CompiledNode, ...]
    """Built nodes in pipeline order."""
    context: LLMContext
    context_aggregator: LLMContextAggregatorPair

    def processor(self, node_id: str) -> FrameProcessor:
        return next(c.processor for c in self.nodes if c.node.id == node_id)

    def pipeline(self, transport: BaseTransport) -> Pipeline:
        """Wire the nodes between the transport's input and output.

        The user context aggregator sits right before the LLM; the assistant one goes
        after the transport output so it only records what was actually spoken.
        """
        processors: list[FrameProcessor] = [transport.input()]
        for compiled in self.nodes:
            if compiled.node.type == "llm":
                processors.append(self.context_aggregator.user())
            processors.append(compiled.processor)
        processors += [transport.output(), self.context_aggregator.assistant()]
        return Pipeline(processors)


def validate(config: AgentConfig, registry: ProviderRegistry) -> list[Issue]:
    """All checks after the JSON Schema: graph shape, providers and their params.

    Doesn't need secrets, so the dashboard can call it while editing.
    """
    _, issues = order_chain(config)
    return issues + _provider_issues(config, registry)


def compile_agent(
    config: AgentConfig,
    registry: ProviderRegistry | None = None,
    env: Mapping[str, str] | None = None,
) -> CompiledAgent:
    """Validate the config, check secrets, and build every node's processor."""
    registry = ProviderRegistry.from_directory() if registry is None else registry
    env = os.environ if env is None else env

    chain, issues = order_chain(config)
    issues += _provider_issues(config, registry)
    issues += _env_issues(config, registry, env)
    if issues:
        raise ConfigError(issues)

    compiled = []
    for node in chain:
        spec = registry.get(node.type, node.provider)
        assert spec is not None  # checked by _provider_issues
        adapter = spec.load_adapter()
        try:
            processor = adapter(spec.with_defaults(node.params), BuildContext(node=node, env=env))
        except Exception as e:
            raise ConfigError([Issue(f"{spec.name} failed to build: {e}", node_id=node.id)]) from e
        compiled.append(CompiledNode(node=node, processor=processor))

    context = LLMContext()
    return CompiledAgent(
        config=config,
        nodes=tuple(compiled),
        context=context,
        context_aggregator=LLMContextAggregatorPair(context),
    )


def _provider_issues(config: AgentConfig, registry: ProviderRegistry) -> list[Issue]:
    issues = []
    for i, node in enumerate(config.nodes):
        spec = registry.get(node.type, node.provider)
        if spec is None:
            available = ", ".join(s.id for s in registry.for_type(node.type)) or "none installed"
            issues.append(
                Issue(
                    f'unknown {node.type} provider "{node.provider}" (available: {available})',
                    node_id=node.id,
                    node_index=i,
                    path=pointer(["nodes", i, "provider"]),
                )
            )
            continue
        for error in spec.params_validator.iter_errors(node.params):
            field = ["params", *error.absolute_path]
            issues.append(
                Issue(
                    describe(error, field),
                    node_id=node.id,
                    node_index=i,
                    path=pointer(["nodes", i, *field]),
                )
            )
    return issues


def _env_issues(
    config: AgentConfig, registry: ProviderRegistry, env: Mapping[str, str]
) -> list[Issue]:
    issues = []
    for i, node in enumerate(config.nodes):
        spec = registry.get(node.type, node.provider)
        for name in spec.missing_env(env) if spec else ():
            issues.append(
                Issue(
                    f"{spec.name} needs the {name} environment variable (add it to .env)",
                    node_id=node.id,
                    node_index=i,
                )
            )
    return issues
