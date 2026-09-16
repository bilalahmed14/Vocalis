from pipecat.services.groq.llm import GroqLLMService

from provider_testing import settings_of


def test_builds_with_defaults_and_system_prompt(build):
    llm = build("llm", "groq", system_prompt="Be brief.")

    assert isinstance(llm, GroqLLMService)
    settings = settings_of(llm)
    assert settings.model == "llama-3.3-70b-versatile"
    assert settings.system_instruction == "Be brief."


def test_params_are_passed_through(build):
    llm = build(
        "llm",
        "groq",
        {"model": "llama-3.1-8b-instant", "temperature": 0.2, "max_tokens": 150},
        system_prompt="x",
    )

    settings = settings_of(llm)
    assert settings.model == "llama-3.1-8b-instant"
    assert settings.temperature == 0.2
    assert settings.max_tokens == 150
