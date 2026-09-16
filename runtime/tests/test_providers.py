"""Provider plugin discovery, manifests, params defaults and lazy adapter loading."""

import pytest

from conftest import write_provider
from vocalis import ProviderError, ProviderRegistry


def test_discovers_plugins(registry):
    assert len(registry) == 5
    assert registry.get("stt", "fake").name == "Fake"
    assert registry.get("stt", "nope") is None
    assert [spec.id for spec in registry.for_type("llm")] == ["fake", "other"]


def test_same_id_can_exist_for_different_types(registry):
    assert registry.get("vad", "fake").type == "vad"
    assert registry.get("tts", "fake").type == "tts"


def test_missing_directory_is_an_empty_registry(tmp_path):
    assert len(ProviderRegistry.from_directory(tmp_path / "nope")) == 0


def test_repo_providers_load():
    ProviderRegistry.from_directory()


def test_with_defaults_fills_only_missing_params(registry):
    spec = registry.get("stt", "fake")

    assert spec.with_defaults({}) == {"model": "large", "language": "en"}
    assert spec.with_defaults({"model": "small"}) == {"model": "small", "language": "en"}


def test_missing_env(registry):
    spec = registry.get("stt", "fake")

    assert spec.missing_env({}) == ["FAKE_STT_KEY"]
    assert spec.missing_env({"FAKE_STT_KEY": ""}) == ["FAKE_STT_KEY"]
    assert spec.missing_env({"FAKE_STT_KEY": "x"}) == []


def test_adapters_are_imported_lazily(tmp_path):
    root = tmp_path / "providers"
    write_provider(root, "tts", "heavy", adapter="raise RuntimeError('imported too early')")

    spec = ProviderRegistry.from_directory(root).get("tts", "heavy")

    with pytest.raises(RuntimeError, match="imported too early"):
        spec.load_adapter()


def test_registries_with_same_provider_id_keep_their_own_adapter(tmp_path):
    for name in ("a", "b"):
        write_provider(tmp_path / name, "tts", "x", adapter=f"def create(p, c): return {name!r}")

    first = ProviderRegistry.from_directory(tmp_path / "a").get("tts", "x")
    second = ProviderRegistry.from_directory(tmp_path / "b").get("tts", "x")

    assert first.load_adapter()({}, None) == "a"
    assert second.load_adapter()({}, None) == "b"


def test_adapter_without_create(tmp_path):
    write_provider(tmp_path, "tts", "empty", adapter="x = 1")
    spec = ProviderRegistry.from_directory(tmp_path).get("tts", "empty")

    with pytest.raises(ProviderError, match="missing create"):
        spec.load_adapter()


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"manifest": {"id": "bad", "type": "tts"}}, 'missing required field "name"'),
        (
            {"manifest": {"id": "bad", "type": "mixer", "name": "B", "params": {"type": "object"}}},
            "type: 'mixer' is not one of",
        ),
        (
            {
                "manifest": {
                    "id": "elsewhere",
                    "type": "tts",
                    "name": "B",
                    "params": {"type": "object"},
                }
            },
            "expected to live in providers/tts/elsewhere/",
        ),
        ({"adapter": None}, "missing adapter.py"),
        (
            {"params": {"type": "object", "properties": {"x": {"type": "nope"}}}},
            "params is not a valid JSON Schema",
        ),
    ],
    ids=["missing-name", "bad-type", "folder-mismatch", "no-adapter", "bad-params-schema"],
)
def test_broken_plugins_fail_loudly(tmp_path, kwargs, error):
    write_provider(tmp_path, "tts", "bad", **kwargs)

    with pytest.raises(ProviderError, match=error) as exc:
        ProviderRegistry.from_directory(tmp_path)
    assert "provider.json" in str(exc.value) or "bad" in str(exc.value)
