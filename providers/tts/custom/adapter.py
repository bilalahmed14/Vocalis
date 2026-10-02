from pipecat.services.openai.tts import OpenAITTSService

OPTIONAL = ("speed",)


def create(params, ctx):
    return OpenAITTSService(
        api_key=ctx.env.get(params.get("api_key_env", ""), "not-needed"),
        base_url=params["base_url"],
        settings=OpenAITTSService.Settings(
            model=params["model"],
            voice=params["voice"],
            **{key: params[key] for key in OPTIONAL if key in params},
        ),
    )
