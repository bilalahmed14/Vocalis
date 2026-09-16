from pipecat.services.openai.llm import OpenAILLMService

from provider_testing import settings_of


def test_builds_with_defaults_and_system_prompt(build):
    llm = build("llm", "openai", system_prompt="Be brief.")

    assert isinstance(llm, OpenAILLMService)
    settings = settings_of(llm)
    assert settings.model == "gpt-4.1-mini"
    assert settings.system_instruction == "Be brief."


def test_optional_params_are_only_set_when_given(build):
    default = settings_of(build("llm", "openai", system_prompt="x"))
    tuned = settings_of(
        build("llm", "openai", {"temperature": 0.3, "max_tokens": 200}, system_prompt="x")
    )

    assert tuned.temperature == 0.3
    assert tuned.max_tokens == 200
    assert default.temperature != 0.3


def test_base_url_points_client_elsewhere(build):
    llm = build("llm", "openai", {"base_url": "http://localhost:11434/v1"}, system_prompt="x")

    assert str(llm._client.base_url).startswith("http://localhost:11434/v1")
