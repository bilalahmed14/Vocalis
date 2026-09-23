from pipecat.services.deepgram.tts import DeepgramTTSService

from provider_testing import settings_of


def test_builds_with_defaults(build):
    tts = build("tts", "deepgram")

    assert isinstance(tts, DeepgramTTSService)
    assert settings_of(tts).voice == "aura-2-helena-en"


def test_params_are_passed_through(build):
    tts = build("tts", "deepgram", {"voice": "aura-2-apollo-en", "speed": 1.1})

    settings = settings_of(tts)
    assert (settings.voice, settings.speed) == ("aura-2-apollo-en", 1.1)


def test_shares_the_key_with_deepgram_stt(registry):
    assert registry.get("tts", "deepgram").env == registry.get("stt", "deepgram").env
