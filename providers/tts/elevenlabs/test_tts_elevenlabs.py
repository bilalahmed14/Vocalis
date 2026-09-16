from pipecat.services.elevenlabs.tts import ElevenLabsTTSService

from provider_testing import settings_of

VOICE = "21m00Tcm4TlvDq8ikWAM"


def test_builds_with_defaults(build):
    tts = build("tts", "elevenlabs", {"voice_id": VOICE})

    assert isinstance(tts, ElevenLabsTTSService)
    settings = settings_of(tts)
    assert settings.voice == VOICE
    assert settings.model == "eleven_flash_v2_5"


def test_voice_settings_are_passed_through(build):
    tts = build(
        "tts",
        "elevenlabs",
        {"voice_id": VOICE, "stability": 0.4, "similarity_boost": 0.9, "speed": 1.1},
    )

    settings = settings_of(tts)
    assert (settings.stability, settings.similarity_boost, settings.speed) == (0.4, 0.9, 1.1)


def test_voice_id_is_required(registry):
    assert registry.get("tts", "elevenlabs").params_schema["required"] == ["voice_id"]
