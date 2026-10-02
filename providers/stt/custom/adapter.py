from pipecat.services.openai.stt import OpenAISTTService

from vocalis.providers import language


def create(params, ctx):
    return OpenAISTTService(
        api_key=ctx.env.get(params.get("api_key_env", ""), "not-needed"),
        base_url=params["base_url"],
        ttfs_p99_latency=params["ttfs_p99_latency"],
        settings=OpenAISTTService.Settings(
            model=params["model"],
            language=language(params["language"]),
        ),
    )
