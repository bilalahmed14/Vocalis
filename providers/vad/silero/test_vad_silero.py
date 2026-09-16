from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.processors.audio.vad_processor import VADProcessor


def test_builds_vad_processor_with_defaults(build):
    vad = build("vad", "silero")

    assert isinstance(vad, VADProcessor)
    analyzer = vad._vad_controller._vad_analyzer
    assert isinstance(analyzer, SileroVADAnalyzer)
    assert analyzer.params.stop_secs == 0.2
    assert analyzer.params.confidence == 0.7


def test_params_are_passed_through(build):
    vad = build("vad", "silero", {"stop_secs": 0.8, "min_volume": 0.3})

    params = vad._vad_controller._vad_analyzer.params
    assert params.stop_secs == 0.8
    assert params.min_volume == 0.3
