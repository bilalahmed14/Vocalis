"""A voice model you're serving yourself."""

from pipecat.services.openai.tts import OpenAITTSService

from provider_testing import settings_of

ENDPOINT = {"base_url": "http://localhost:8880/v1", "model": "kokoro", "voice": "af_heart"}


def test_builds_against_your_endpoint(build):
    tts = build("tts", "custom", ENDPOINT)

    assert isinstance(tts, OpenAITTSService)
    settings = settings_of(tts)
    assert (settings.model, settings.voice) == ("kokoro", "af_heart")


def test_speed_is_optional(build):
    assert settings_of(build("tts", "custom", {**ENDPOINT, "speed": 1.2})).speed == 1.2
