"""Checks every provider plugin must pass, whatever its type."""

import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from vocalis import ProviderRegistry
from vocalis.paths import REPO_ROOT

SPECS = list(ProviderRegistry.from_directory())


def test_expected_providers_are_installed():
    installed = {(spec.type, spec.id) for spec in SPECS}

    assert installed == {
        ("vad", "silero"),
        ("stt", "deepgram"),
        ("stt", "whisper"),
        ("stt", "moonshine"),
        ("llm", "openai"),
        ("llm", "anthropic"),
        ("llm", "groq"),
        ("llm", "ollama"),
        ("tts", "elevenlabs"),
        ("tts", "cartesia"),
        ("tts", "deepgram"),
        ("tts", "kokoro"),
    }


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: f"{s.type}/{s.id}")
def test_has_icon(spec):
    assert (spec.path / "icon.svg").is_file()


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: f"{s.type}/{s.id}")
def test_defaults_and_examples_are_valid(spec):
    properties = spec.params_schema.get("properties", {})
    for name, prop in properties.items():
        values = ([prop["default"]] if "default" in prop else []) + prop.get("examples", [])
        for value in values:
            errors = list(Draft202012Validator(prop).iter_errors(value))
            assert errors == [], f"{name}={value!r}: {errors[0].message}"


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: f"{s.type}/{s.id}")
def test_required_params_have_an_example(spec):
    """So the canvas can pre-fill a new node and tests can build it."""
    properties = spec.params_schema.get("properties", {})
    for name in spec.params_schema.get("required", []):
        assert properties[name].get("examples"), f"required param {name!r} has no example"


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: f"{s.type}/{s.id}")
def test_params_reject_unknown_keys(spec):
    """A typo in a config should be an error, not silently ignored."""
    assert spec.params_schema.get("additionalProperties") is False


def test_env_example_lists_every_provider_secret():
    env_example = (REPO_ROOT / ".env.example").read_text()
    documented = set(re.findall(r"^([A-Z][A-Z0-9_]*)=", env_example, re.MULTILINE))

    needed = {name for spec in SPECS for name in spec.env}

    assert needed <= documented, f"add to .env.example: {sorted(needed - documented)}"


def test_adapters_only_import_pipecat_and_vocalis():
    """Adapters stay thin: provider SDKs are reached through Pipecat services."""
    for spec in SPECS:
        source = Path(spec.path / "adapter.py").read_text()
        modules = re.findall(r"^\s*(?:from|import) ([a-z_]+)", source, re.MULTILINE)
        assert set(modules) <= {"pipecat", "vocalis"}, f"{spec.type}/{spec.id}: {modules}"
