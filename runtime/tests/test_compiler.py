"""The compiler: provider checks, secrets, building processors and wiring the pipeline."""

import pytest
from pipecat.processors.aggregators.llm_response_universal import (
    LLMAssistantAggregator,
    LLMUserAggregator,
)
from pipecat.processors.frame_processor import FrameProcessor

from conftest import write_provider
from vocalis import ConfigError, ProviderRegistry, compile_agent, parse_config, validate


class StubTransport:
    def __init__(self):
        self._input = FrameProcessor(name="mic")
        self._output = FrameProcessor(name="speaker")

    def input(self):
        return self._input

    def output(self):
        return self._output


def compile_issues(config, registry, env) -> list[str]:
    with pytest.raises(ConfigError) as exc:
        compile_agent(parse_config(config), registry, env)
    return [str(issue) for issue in exc.value.issues]


def test_valid_config_has_no_issues(config, registry):
    assert validate(parse_config(config), registry) == []


def test_builds_nodes_in_chain_order(config, registry, env):
    config["nodes"].reverse()

    agent = compile_agent(parse_config(config), registry, env)

    assert [c.node.id for c in agent.nodes] == ["vad", "stt", "llm", "tts"]
    assert [c.processor.name for c in agent.nodes] == ["vad", "stt", "llm", "tts"]


def test_adapter_gets_params_with_defaults_node_and_env(config, registry, env):
    agent = compile_agent(parse_config(config), registry, env)

    stt = agent.processor("stt")
    assert stt.params == {"model": "small", "language": "en"}
    assert stt.ctx.secret("FAKE_STT_KEY") == "secret"
    assert agent.processor("llm").ctx.node.system_prompt == "Be brief."


def test_pipeline_wires_context_aggregators_around_llm(config, registry, env):
    agent = compile_agent(parse_config(config), registry, env)
    transport = StubTransport()

    processors = agent.pipeline(transport).processors[1:-1]  # drop Pipeline source/sink

    names = [p.name for p in processors]
    assert names[:3] == ["mic", "vad", "stt"]
    assert isinstance(processors[3], LLMUserAggregator)
    assert names[4:7] == ["llm", "tts", "speaker"]
    assert isinstance(processors[7], LLMAssistantAggregator)
    assert len(processors) == 8


def test_unknown_provider_lists_available_ones(config, registry, env):
    config["nodes"][2]["provider"] = "gpt"

    assert compile_issues(config, registry, env) == [
        'node "llm": unknown llm provider "gpt" (available: fake, other)'
    ]


def test_unknown_provider_with_none_installed(config, registry, env):
    no_vad = ProviderRegistry(spec for spec in registry if spec.type != "vad")
    config["nodes"][0]["provider"] = "silero"

    assert compile_issues(config, no_vad, env) == [
        'node "vad": unknown vad provider "silero" (available: none installed)'
    ]


def test_params_are_validated_against_provider_schema(config, registry, env):
    config["nodes"][1]["params"] = {"model": "huge", "api_key": "x"}

    issues = validate(parse_config(config), registry)

    assert [str(i) for i in issues] == [
        'node "stt": params: unknown field "api_key"',
        "node \"stt\": params.model: 'huge' is not one of ['small', 'large']",
    ]
    assert issues[1].path == "/nodes/1/params/model"


def test_missing_secret_blocks_compile_but_not_validate(config, registry):
    assert validate(parse_config(config), registry) == []
    assert compile_issues(config, registry, env={}) == [
        'node "stt": Fake needs the FAKE_STT_KEY environment variable (add it to .env)'
    ]


def test_graph_and_provider_issues_are_reported_together(config, registry, env):
    config["nodes"][2]["provider"] = "gpt"
    config["edges"].pop()

    issues = compile_issues(config, registry, env)

    assert any("not connected" in issue for issue in issues)
    assert any('unknown llm provider "gpt"' in issue for issue in issues)


def test_adapter_failure_points_at_node(config, providers_root, env):
    write_provider(
        providers_root, "tts", "broken", adapter="def create(p, c): raise ValueError('bad voice')"
    )
    config["nodes"][3]["provider"] = "broken"

    issues = compile_issues(config, ProviderRegistry.from_directory(providers_root), env)

    assert issues == ['node "tts": Broken failed to build: bad voice']
