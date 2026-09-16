from pipecat.services.deepgram.stt import DeepgramSTTService

from vocalis.providers import language


def create(params, ctx):
    return DeepgramSTTService(
        api_key=ctx.secret("DEEPGRAM_API_KEY"),
        settings=DeepgramSTTService.Settings(
            model=params["model"],
            language=language(params["language"]),
            smart_format=params["smart_format"],
            keyterm=params["keyterms"] or None,
        ),
    )
