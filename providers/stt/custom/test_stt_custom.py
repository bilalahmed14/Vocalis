"""A transcription server you're running yourself."""

from pipecat.services.openai.stt import OpenAISTTService

from provider_testing import settings_of

ENDPOINT = {"base_url": "http://localhost:8000/v1", "model": "whisper-1"}


def test_builds_against_your_endpoint(build):
    stt = build("stt", "custom", ENDPOINT)

    assert isinstance(stt, OpenAISTTService)
    assert settings_of(stt).model == "whisper-1"


def test_it_needs_a_vad_and_declares_a_grace_window(build, registry):
    spec = registry.get("stt", "custom")

    assert spec.needs_vad
    assert build("stt", "custom", ENDPOINT)._ttfs_p99_latency == 0.5
