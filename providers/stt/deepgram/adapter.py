from pipecat.services.deepgram.stt import DeepgramSTTService

from vocalis.providers import language


def create(params, ctx):
    return DeepgramSTTService(
        api_key=ctx.secret("DEEPGRAM_API_KEY"),
        **(
            {"ttfs_p99_latency": params["ttfs_p99_latency"]} if "ttfs_p99_latency" in params else {}
        ),
        settings=DeepgramSTTService.Settings(
            model=params["model"],
            language=language(params["language"]),
            smart_format=params["smart_format"],
            keyterm=params["keyterms"] or None,
        ),
    )
