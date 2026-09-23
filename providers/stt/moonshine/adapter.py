from vocalis.providers import language


def create(params, ctx):
    from pipecat.services.moonshine.stt import MoonshineSTTService

    return MoonshineSTTService(
        ttfs_p99_latency=params["ttfs_p99_latency"],
        settings=MoonshineSTTService.Settings(
            model=params["model"],
            language=language(params["language"]),
        ),
    )
