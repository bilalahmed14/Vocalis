"""The sounddevice transport, with fake streams standing in for real devices."""

import asyncio

from pipecat.frames.frames import EndFrame, InputAudioRawFrame, OutputAudioRawFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.workers.runner import WorkerRunner

from vocalis_cli import audio
from vocalis_cli.audio import LocalAudioParams, LocalAudioTransport


class FakeStream:
    instances: list["FakeStream"] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.started = False
        self.closed = False
        self.written = bytearray()
        FakeStream.instances.append(self)

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

    def close(self):
        self.closed = True

    def write(self, data):
        self.written += data


class Loopback(FrameProcessor):
    """Plays mic audio straight back out, standing in for STT -> LLM -> TTS."""

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if isinstance(frame, InputAudioRawFrame):
            frame = OutputAudioRawFrame(
                audio=frame.audio, sample_rate=frame.sample_rate, num_channels=frame.num_channels
            )
        await self.push_frame(frame, direction)


def test_mic_audio_reaches_speaker(monkeypatch):
    FakeStream.instances = []
    monkeypatch.setattr(audio.sd, "RawInputStream", FakeStream)
    monkeypatch.setattr(audio.sd, "RawOutputStream", FakeStream)

    transport = LocalAudioTransport(
        LocalAudioParams(audio_in_enabled=True, audio_out_enabled=True, input_device=3)
    )
    pipeline = Pipeline([transport.input(), Loopback(), transport.output()])
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(audio_in_sample_rate=16000, audio_out_sample_rate=16000),
    )
    chunk = b"\x01\x00" * 320  # 20 ms of 16 kHz mono int16

    async def speak():
        while not (FakeStream.instances and FakeStream.instances[0].started):
            await asyncio.sleep(0.01)
        mic = FakeStream.instances[0]
        for _ in range(10):
            mic.kwargs["callback"](chunk, 320, None, None)
        await asyncio.sleep(0.5)
        await worker.queue_frame(EndFrame())

    async def main():
        runner = WorkerRunner(handle_sigint=False)
        await asyncio.wait_for(asyncio.gather(runner.run(worker), speak()), timeout=10)

    asyncio.run(main())

    mic, speaker = FakeStream.instances
    assert mic.kwargs["samplerate"] == 16000
    assert mic.kwargs["blocksize"] == 320
    assert mic.kwargs["device"] == 3
    assert mic.closed and speaker.closed
    assert len(speaker.written) >= len(chunk) * 8
