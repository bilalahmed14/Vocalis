from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.processors.audio.vad_processor import VADProcessor


def create(params, ctx):
    return VADProcessor(vad_analyzer=SileroVADAnalyzer(params=VADParams(**params)))
