from vocalis.providers import language


def create(params, ctx):
    from pipecat.services.kokoro.tts import KokoroTTSService

    return KokoroTTSService(
        settings=KokoroTTSService.Settings(
            voice=params["voice_id"],
            speed=params["speed"],
            language=language(params["language"]),
        ),
    )
