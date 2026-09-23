"""Time each stage of an agent on a recorded utterance, without a microphone.

    uv run examples/latency_check.py examples/local.json [speech.wav]

Speaks a sample line with macOS `say` when no WAV is given, then pushes it through
the agent's own STT, LLM and TTS nodes and reports what each stage cost. Use it to
compare configs (models, providers, params) repeatably before testing by voice.
"""

import asyncio
import subprocess
import sys
import time
import wave
from pathlib import Path

from loguru import logger

from vocalis import compile_agent, load_config

SAMPLE_TEXT = "What is the tallest mountain in Africa?"


def sample_audio(path: Path) -> bytes:
    """Record the sample line with macOS text-to-speech, as 16 kHz mono PCM."""
    if not path.exists():
        aiff = path.with_suffix(".aiff")
        subprocess.run(["say", "-o", str(aiff), SAMPLE_TEXT], check=True)
        subprocess.run(
            ["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(aiff), str(path)],
            check=True,
        )
    with wave.open(str(path)) as audio:
        return audio.readframes(audio.getnframes())


async def main(config_path: str, wav_path: str) -> int:
    logger.remove()
    logger.add(sys.stderr, level="WARNING")

    audio = sample_audio(Path(wav_path))
    agent = compile_agent(load_config(config_path))
    stages = {compiled.node.type: compiled.processor for compiled in agent.nodes}

    # Each stage is timed on its own here rather than inside a running pipeline, so
    # the TTS never sees the StartFrame that would tell it the output sample rate.
    if not getattr(stages["tts"], "sample_rate", 0):
        stages["tts"]._sample_rate = 24000

    print(
        f"{agent.config.name}: "
        + " -> ".join(f"{c.node.type}:{c.node.provider}" for c in agent.nodes)
    )
    print(f"input: {len(audio) / 32000:.1f}s of speech\n")

    from pipecat.frames.frames import TextFrame

    # STT
    started = time.perf_counter()
    transcript = ""
    async for frame in stages["stt"].run_stt(audio):
        if isinstance(frame, TextFrame):
            transcript += frame.text
    stt_secs = time.perf_counter() - started
    print(f"  stt   {stt_secs * 1000:7.0f} ms   “{transcript.strip()}”")

    # LLM: time to first token is what a caller actually feels.
    from pipecat.processors.aggregators.llm_context import LLMContext

    context = LLMContext(messages=[{"role": "user", "content": transcript.strip() or SAMPLE_TEXT}])
    started = time.perf_counter()
    first_token = None
    reply = ""
    llm = stages["llm"]
    if hasattr(llm, "get_chat_completions"):
        # OpenAI-compatible services (OpenAI, Groq, Ollama) stream chunks, so the
        # harness can report time to first token, which is what the caller feels.
        async for chunk in await llm.get_chat_completions(context):
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                first_token = first_token or time.perf_counter() - started
                reply += delta
    else:
        reply = await llm.run_inference(context) or ""
    llm_secs = time.perf_counter() - started
    print(f"  llm   {llm_secs * 1000:7.0f} ms   first token {(first_token or 0) * 1000:.0f} ms")
    print(f"        “{reply.strip()[:80]}”")

    # TTS: in a running pipeline the LLM's stream is aggregated into sentences and
    # each is synthesized as it completes, so what the caller waits for is the first
    # sentence, not the whole reply.
    from pipecat.utils.string import match_endofsentence

    spoken_text = reply.strip() or "Kilimanjaro."
    end = match_endofsentence(spoken_text)
    first_sentence = spoken_text[:end] if end else spoken_text

    started = time.perf_counter()
    first_audio = None
    audio_bytes = 0
    async for frame in stages["tts"].run_tts(first_sentence, "latency-check"):
        # Services differ in which audio frame class they yield; any of them counts.
        if getattr(frame, "audio", None):
            first_audio = first_audio or time.perf_counter() - started
            audio_bytes += len(frame.audio)
    tts_secs = time.perf_counter() - started
    spoken = audio_bytes / 48000  # 24 kHz mono 16-bit
    realtime = tts_secs / spoken if spoken else 0
    print(
        f"  tts   {tts_secs * 1000:7.0f} ms   first audio {(first_audio or 0) * 1000:.0f} ms"
        f"   ({spoken:.1f}s of speech, {realtime:.2f}x realtime)"
    )
    print(f"        first sentence: \u201c{first_sentence}\u201d")

    turn = stt_secs + (first_token or 0) + (first_audio or 0)
    print(f"\n  user stops speaking -> first audio out: {turn * 1000:.0f} ms")
    if realtime > 0.3:
        print(
            f"  note: this TTS synthesizes at {realtime:.2f}x realtime and emits nothing until a\n"
            "        sentence is finished, so every extra word of the reply adds delay."
        )
    return 0


if __name__ == "__main__":
    config = sys.argv[1] if len(sys.argv) > 1 else "examples/local.json"
    wav = sys.argv[2] if len(sys.argv) > 2 else "/tmp/vocalis-sample.wav"
    sys.exit(asyncio.run(main(config, wav)))
