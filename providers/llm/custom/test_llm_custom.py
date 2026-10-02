"""Pointing a pipeline at a model you're serving yourself."""

from pipecat.services.openai.llm import OpenAILLMService

from provider_testing import settings_of

ENDPOINT = {"base_url": "http://localhost:8000/v1", "model": "my-model"}


def test_builds_against_your_endpoint(build):
    llm = build("llm", "custom", ENDPOINT, system_prompt="Be brief.")

    assert isinstance(llm, OpenAILLMService)
    assert str(llm._client.base_url).startswith("http://localhost:8000/v1")
    assert settings_of(llm).model == "my-model"
    assert settings_of(llm).system_instruction == "Be brief."


def test_a_server_that_needs_no_key_still_works(build):
    """Most local servers ignore the key, but the client insists on one."""
    llm = build("llm", "custom", ENDPOINT, system_prompt="x")

    assert llm._client.api_key == "not-needed"


def test_the_key_comes_from_the_environment_not_the_config(registry, monkeypatch):
    from vocalis import BuildContext, Node

    monkeypatch.setenv("MY_MODEL_API_KEY", "secret")
    spec = registry.get("llm", "custom")
    params = {**ENDPOINT, "api_key_env": "MY_MODEL_API_KEY"}
    node = Node(id="llm", type="llm", provider="custom", params=params, system_prompt="x")

    import os

    llm = spec.load_adapter()(spec.with_defaults(params), BuildContext(node=node, env=os.environ))

    assert llm._client.api_key == "secret"
    # The config names the variable; the value stays out of it.
    assert "secret" not in str(params)


def test_endpoint_and_model_are_required(registry):
    schema = registry.get("llm", "custom").params_schema

    assert schema["required"] == ["base_url", "model"]
