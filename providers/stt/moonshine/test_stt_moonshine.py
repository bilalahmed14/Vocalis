import pytest

from provider_testing import settings_of

moonshine_stt = pytest.importorskip(
    "pipecat.services.moonshine.stt",
    reason="local extras not installed (uv sync --extra local)",
    exc_type=ImportError,
)


@pytest.fixture(autouse=True)
def no_model_download(monkeypatch):
    """The service downloads the model when it loads; skip that in tests."""
    monkeypatch.setattr(moonshine_stt.MoonshineSTTService, "_load", lambda self: None)


def test_builds_with_defaults(build):
    stt = build("stt", "moonshine")

    assert isinstance(stt, moonshine_stt.MoonshineSTTService)
    assert settings_of(stt).model == "base"


def test_params_are_passed_through(build):
    stt = build("stt", "moonshine", {"model": "tiny-streaming", "language": "en"})

    assert settings_of(stt).model == "tiny-streaming"


def test_needs_vad_and_an_extra(registry):
    spec = registry.get("stt", "moonshine")

    assert spec.needs_vad
    assert spec.requires == {"module": "moonshine_voice", "extra": "local"}


def test_transcript_grace_window_is_declared(build, registry):
    """Without a value the pipeline waits a full second after every turn."""
    assert (
        registry.get("stt", "moonshine").params_schema["properties"]["ttfs_p99_latency"]["default"]
        == 0.3
    )
    assert build("stt", "moonshine")._ttfs_p99_latency == 0.3
    assert build("stt", "moonshine", {"ttfs_p99_latency": 0.15})._ttfs_p99_latency == 0.15
