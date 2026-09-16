"""Helpers for provider adapter tests."""

from typing import Any

from pipecat.processors.frame_processor import FrameProcessor


def settings_of(service: FrameProcessor) -> Any:
    """The service's resolved settings (Pipecat keeps them on a private attribute)."""
    return service._settings
