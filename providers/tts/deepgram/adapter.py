from pipecat.services.deepgram.tts import DeepgramTTSService

OPTIONAL = ("speed",)


def create(params, ctx):
    return DeepgramTTSService(
        api_key=ctx.secret("DEEPGRAM_API_KEY"),
        settings=DeepgramTTSService.Settings(
            voice=params["voice"],
            **{key: params[key] for key in OPTIONAL if key in params},
        ),
    )
