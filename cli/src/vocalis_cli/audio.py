"""Local mic and speaker transport for Pipecat, built on sounddevice.

Pipecat ships a PyAudio-based local transport, but PyAudio has to be compiled
against PortAudio. sounddevice's wheels bundle PortAudio on macOS and Windows, so
`vocalis run` works straight after `uv sync`.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import sounddevice as sd
from pipecat.frames.frames import InputAudioRawFrame, OutputAudioRawFrame, StartFrame
from pipecat.processors.frame_processor import FrameProcessor, FrameProcessorSetup
from pipecat.transports.base_input import BaseInputTransport
from pipecat.transports.base_output import BaseOutputTransport
from pipecat.transports.base_transport import BaseTransport, TransportParams


class LocalAudioParams(TransportParams):
    """Transport params plus the sound devices to use (index or name; None = default)."""

    input_device: int | str | None = None
    output_device: int | str | None = None


class MicInput(BaseInputTransport):
    _params: LocalAudioParams

    def __init__(self, params: LocalAudioParams):
        super().__init__(params)
        self._stream: sd.RawInputStream | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def setup(self, setup: FrameProcessorSetup):
        await super().setup(setup)
        self._stream = sd.RawInputStream(
            samplerate=self.sample_rate,
            channels=self._params.audio_in_channels,
            dtype="int16",
            blocksize=self.sample_rate // 50,  # 20 ms per callback
            device=self._params.input_device,
            callback=self._on_audio,
        )

    async def start(self, frame: StartFrame):
        await super().start(frame)
        if self._stream:
            self._loop = self.get_event_loop()
            self._stream.start()
            await self.set_transport_ready(frame)

    async def cleanup(self):
        await super().cleanup()
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _on_audio(self, data, frames, time, status):
        """Runs on sounddevice's audio thread; hand the chunk to the event loop."""
        if self._loop is None:
            return
        frame = InputAudioRawFrame(
            audio=bytes(data),
            sample_rate=self.sample_rate,
            num_channels=self._params.audio_in_channels,
        )
        asyncio.run_coroutine_threadsafe(self.push_audio_frame(frame), self._loop)


class SpeakerOutput(BaseOutputTransport):
    _params: LocalAudioParams

    def __init__(self, params: LocalAudioParams):
        super().__init__(params)
        self._stream: sd.RawOutputStream | None = None
        # Writes block until the device takes the audio; keep them off the event loop.
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def setup(self, setup: FrameProcessorSetup):
        await super().setup(setup)
        self._stream = sd.RawOutputStream(
            samplerate=self.sample_rate,
            channels=self._params.audio_out_channels,
            dtype="int16",
            device=self._params.output_device,
        )

    async def start(self, frame: StartFrame):
        await super().start(frame)
        if self._stream:
            self._stream.start()
            await self.set_transport_ready(frame)

    async def write_audio_frame(self, frame: OutputAudioRawFrame) -> bool:
        if not self._stream:
            return False
        await self.get_event_loop().run_in_executor(self._executor, self._stream.write, frame.audio)
        return True

    async def cleanup(self):
        try:
            await super().cleanup()
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
        finally:
            self._executor.shutdown(wait=False)


class LocalAudioTransport(BaseTransport):
    """The machine's microphone in, its speakers out."""

    def __init__(self, params: LocalAudioParams):
        super().__init__()
        self._params = params
        self._input: MicInput | None = None
        self._output: SpeakerOutput | None = None

    def input(self) -> FrameProcessor:
        if self._input is None:
            self._input = MicInput(self._params)
        return self._input

    def output(self) -> FrameProcessor:
        if self._output is None:
            self._output = SpeakerOutput(self._params)
        return self._output
