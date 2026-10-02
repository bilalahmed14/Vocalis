"""How much work each model did, not just how long the caller waited.

Latency alone can't tell a fast model from a terse one: an LLM that answers in four
words looks quicker than one that answers in forty. Pipecat reports what each service
actually produced — tokens, characters, seconds of audio — so a turn can also carry
tokens per second, characters per second, and how far ahead of real time the speech
was generated.
"""

from dataclasses import dataclass

from pipecat.frames.frames import MetricsFrame
from pipecat.metrics.metrics import (
    LLMUsageMetricsData,
    STTUsageMetricsData,
    TTSUsageMetricsData,
)
from pipecat.observers.base_observer import BaseObserver, FramePushed


@dataclass
class Work:
    """What one service produced during a turn."""

    tokens: int = 0
    characters: int = 0
    audio_seconds: float = 0.0

    def rate(self, secs: float) -> dict[str, float]:
        """Work per second, given how long the service took to produce it."""
        if secs <= 0:
            return {}
        if self.tokens:
            return {"tokens_per_sec": round(self.tokens / secs, 1)}
        if self.characters:
            return {"chars_per_sec": round(self.characters / secs, 1)}
        if self.audio_seconds:
            # Above 1 means the model produced speech faster than it plays, which is
            # what a live call needs.
            return {"realtime_factor": round(self.audio_seconds / secs, 2)}
        return {}


class ThroughputObserver(BaseObserver):
    """Collects per-service usage as it is reported."""

    def __init__(self):
        super().__init__()
        self._work: dict[str, Work] = {}

    async def on_push_frame(self, data: FramePushed) -> None:
        if not isinstance(data.frame, MetricsFrame):
            return
        for metric in data.frame.data:
            work = self._work.setdefault(getattr(metric, "processor", "") or "", Work())
            if isinstance(metric, LLMUsageMetricsData):
                work.tokens += metric.value.completion_tokens
            elif isinstance(metric, TTSUsageMetricsData):
                work.characters += metric.value
            elif isinstance(metric, STTUsageMetricsData):
                work.audio_seconds += metric.value.audio_seconds

    def take(self) -> dict[str, Work]:
        """Hand over what's been collected and start the next turn empty."""
        collected, self._work = self._work, {}
        return collected
