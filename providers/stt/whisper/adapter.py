from vocalis.providers import language


def create(params, ctx):
    try:
        from pipecat.services.whisper.stt import WhisperSTTService
    except Exception as e:
        raise RuntimeError("local Whisper isn't installed; run: uv sync --extra whisper") from e

    return WhisperSTTService(
        ttfs_p99_latency=params["ttfs_p99_latency"],
        device=params["device"],
        compute_type=params["compute_type"],
        settings=WhisperSTTService.Settings(
            model=params["model"],
            language=language(params["language"]),
            no_speech_prob=params["no_speech_prob"],
        ),
    )
