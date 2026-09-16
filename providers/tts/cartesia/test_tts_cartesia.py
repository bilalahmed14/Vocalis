from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.transcriptions.language import Language

from provider_testing import settings_of

VOICE = "71a7ad14-091c-4e8e-a314-022ece01c121"


def test_builds_with_defaults(build):
    tts = build("tts", "cartesia", {"voice_id": VOICE})

    assert isinstance(tts, CartesiaTTSService)
    settings = settings_of(tts)
    assert settings.voice == VOICE
    assert settings.model == "sonic-3"
    assert settings.language == Language.EN


def test_params_are_passed_through(build):
    tts = build("tts", "cartesia", {"voice_id": VOICE, "model": "sonic-2", "language": "de"})

    settings = settings_of(tts)
    assert settings.model == "sonic-2"
    assert settings.language == Language.DE


def test_voice_id_is_required(registry):
    assert registry.get("tts", "cartesia").params_schema["required"] == ["voice_id"]
