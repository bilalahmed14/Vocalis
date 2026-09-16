from pipecat.services.anthropic.llm import AnthropicLLMService

from provider_testing import settings_of


def test_builds_with_defaults_and_system_prompt(build):
    llm = build("llm", "anthropic", system_prompt="Be brief.")

    assert isinstance(llm, AnthropicLLMService)
    settings = settings_of(llm)
    assert settings.model == "claude-opus-5"
    assert settings.system_instruction == "Be brief."
    assert settings.extra == {}


def test_effort_goes_into_request_body(build):
    llm = build("llm", "anthropic", {"effort": "low"}, system_prompt="x")

    assert settings_of(llm).extra == {"extra_body": {"output_config": {"effort": "low"}}}


def test_max_tokens(build):
    llm = build("llm", "anthropic", {"max_tokens": 300}, system_prompt="x")

    assert settings_of(llm).max_tokens == 300


def test_sampling_params_are_not_offered(registry):
    """Current Claude models reject temperature/top_p/top_k."""
    properties = registry.get("llm", "anthropic").params_schema["properties"]

    assert not {"temperature", "top_p", "top_k"} & set(properties)
