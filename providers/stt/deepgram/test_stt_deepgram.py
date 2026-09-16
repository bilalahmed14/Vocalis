from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.transcriptions.language import Language

from provider_testing import settings_of


def test_builds_with_defaults(build):
    stt = build("stt", "deepgram")

    assert isinstance(stt, DeepgramSTTService)
    settings = settings_of(stt)
    assert settings.model == "nova-3"
    assert settings.language == Language.EN
    assert settings.smart_format is False
    assert settings.keyterm is None


def test_params_are_passed_through(build):
    stt = build(
        "stt",
        "deepgram",
        {"model": "nova-2", "language": "es", "smart_format": True, "keyterms": ["Vocalis"]},
    )

    settings = settings_of(stt)
    assert settings.model == "nova-2"
    assert settings.language == Language.ES
    assert settings.smart_format is True
    assert settings.keyterm == ["Vocalis"]


def test_service_specific_language_is_passed_as_is(build):
    stt = build("stt", "deepgram", {"language": "multi"})

    assert settings_of(stt).language == "multi"
