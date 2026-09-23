import pytest

from provider_testing import settings_of

kokoro_tts = pytest.importorskip(
    "pipecat.services.kokoro.tts",
    reason="local extras not installed (uv sync --extra local)",
    exc_type=ImportError,
)


class FakeKokoro:
    """Stands in for the ONNX model, which is ~350MB and downloads on first use."""

    voices = {"af_heart": None, "bm_george": None}


@pytest.fixture(autouse=True)
def no_model_download(monkeypatch):
    monkeypatch.setattr(kokoro_tts, "_ensure_model_files", lambda *a, **k: None)
    monkeypatch.setattr(kokoro_tts, "Kokoro", lambda *a, **k: FakeKokoro())


def test_builds_with_defaults(build):
    tts = build("tts", "kokoro")

    assert isinstance(tts, kokoro_tts.KokoroTTSService)
    settings = settings_of(tts)
    assert settings.voice == "af_heart"
    assert settings.speed == 1


def test_params_are_passed_through(build):
    tts = build("tts", "kokoro", {"voice_id": "bm_george", "speed": 1.2})

    settings = settings_of(tts)
    assert (settings.voice, settings.speed) == ("bm_george", 1.2)


def test_needs_no_api_key(registry):
    assert registry.get("tts", "kokoro").env == ()
