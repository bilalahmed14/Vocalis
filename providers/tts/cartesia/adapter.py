from pipecat.services.cartesia.tts import CartesiaTTSService

from vocalis.providers import language


def create(params, ctx):
    return CartesiaTTSService(
        api_key=ctx.secret("CARTESIA_API_KEY"),
        settings=CartesiaTTSService.Settings(
            voice=params["voice_id"],
            model=params["model"],
            language=language(params["language"]),
        ),
    )
