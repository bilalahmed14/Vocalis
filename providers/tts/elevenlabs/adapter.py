from pipecat.services.elevenlabs.tts import ElevenLabsTTSService

OPTIONAL = ("stability", "similarity_boost", "speed")


def create(params, ctx):
    return ElevenLabsTTSService(
        api_key=ctx.secret("ELEVENLABS_API_KEY"),
        settings=ElevenLabsTTSService.Settings(
            voice=params["voice_id"],
            model=params["model"],
            **{key: params[key] for key in OPTIONAL if key in params},
        ),
    )
