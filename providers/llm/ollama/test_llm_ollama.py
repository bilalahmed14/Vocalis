from pipecat.services.ollama.llm import OLLamaLLMService

from provider_testing import settings_of


def test_builds_with_defaults_and_system_prompt(build):
    llm = build("llm", "ollama", system_prompt="Be brief.")

    assert isinstance(llm, OLLamaLLMService)
    settings = settings_of(llm)
    assert settings.model == "llama3.2:3b"
    assert settings.system_instruction == "Be brief."
    assert str(llm._client.base_url).startswith("http://localhost:11434/v1")


def test_points_at_another_ollama(build):
    llm = build(
        "llm",
        "ollama",
        {"base_url": "http://host.docker.internal:11434/v1", "model": "qwen3:4b"},
        system_prompt="x",
    )

    assert str(llm._client.base_url).startswith("http://host.docker.internal:11434/v1")
    assert settings_of(llm).model == "qwen3:4b"


def test_needs_no_api_key(registry):
    assert registry.get("llm", "ollama").env == ()
