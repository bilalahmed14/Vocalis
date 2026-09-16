import pytest

from provider_testing import settings_of

whisper_stt = pytest.importorskip(
    "pipecat.services.whisper.stt",
    reason="local Whisper not installed (uv sync --extra whisper)",
    exc_type=ImportError,
)


@pytest.fixture(autouse=True)
def no_model_download(monkeypatch):
    """The service loads (and downloads) the model in __init__; skip that in tests."""
    monkeypatch.setattr(whisper_stt.WhisperSTTService, "_load", lambda self: None)


def test_builds_with_defaults(build):
    stt = build("stt", "whisper")

    assert isinstance(stt, whisper_stt.WhisperSTTService)
    assert settings_of(stt).model == "Systran/faster-distil-whisper-medium.en"
    assert stt._device == "auto"
    assert stt._compute_type == "default"


def test_params_are_passed_through(build):
    stt = build(
        "stt",
        "whisper",
        {"model": "small", "language": "fr", "device": "cpu", "compute_type": "int8"},
    )

    settings = settings_of(stt)
    assert settings.model == "small"
    assert str(settings.language) == "fr"
    assert stt._device == "cpu"
    assert stt._compute_type == "int8"


def test_needs_vad(registry):
    assert registry.get("stt", "whisper").needs_vad
