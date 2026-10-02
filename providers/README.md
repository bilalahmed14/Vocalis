# Providers

Each provider is a plugin folder, `providers/<type>/<id>/`:

| File                  | What it is                                                         |
| --------------------- | ------------------------------------------------------------------ |
| `provider.json`       | Manifest: name, required env vars, JSON Schema for `params`        |
| `adapter.py`          | `create(params, ctx)` returning a Pipecat processor                |
| `icon.svg`            | Palette icon for the canvas                                        |
| `test_<type>_<id>.py` | Adapter tests                                                      |

The runtime discovers plugins by scanning this folder, so nothing else needs
registering. Manifests are validated against
[`schema/provider.v1.schema.json`](../schema/provider.v1.schema.json), which also
covers two optional declarations the compiler acts on:

- `env`: environment variables the provider needs, checked before a run starts
- `requires`: `{"module": "faster_whisper", "extra": "whisper"}` for an optional
  dependency, so a missing one is reported as "run: uv sync --extra whisper"
- `needs_vad`: the provider only works with a `vad` node in the pipeline

## Installed

| Type | Provider   | Needs                  |
| ---- | ---------- | ---------------------- |
| vad  | silero     | nothing (runs locally) |
| stt  | deepgram   | `DEEPGRAM_API_KEY`     |
| stt  | whisper    | `uv sync --extra whisper`; runs locally |
| stt  | moonshine  | `uv sync --extra local`; runs locally   |
| stt  | custom     | your own transcription endpoint         |
| llm  | openai     | `OPENAI_API_KEY`       |
| llm  | anthropic  | `ANTHROPIC_API_KEY`    |
| llm  | groq       | `GROQ_API_KEY`         |
| llm  | ollama     | nothing (Ollama on your machine)        |
| llm  | custom     | your own chat endpoint                  |
| tts  | elevenlabs | `ELEVENLABS_API_KEY`   |
| tts  | cartesia   | `CARTESIA_API_KEY`     |
| tts  | deepgram   | `DEEPGRAM_API_KEY`     |
| tts  | kokoro     | `uv sync --extra local`; runs locally   |
| tts  | custom     | your own speech endpoint                |

## Testing your own model

Every stage has a **`custom`** provider that points at an OpenAI-compatible endpoint,
so a model you're serving yourself can be dropped into a real call beside whichever
providers you already trust:

```json
{
  "id": "llm",
  "type": "llm",
  "provider": "custom",
  "system_prompt": "Answer in one short sentence.",
  "params": {
    "base_url": "http://localhost:8000/v1",
    "model": "my-model",
    "api_key_env": "MY_MODEL_API_KEY"
  }
}
```

That covers vLLM, llama.cpp, LM Studio, SGLang, TGI and anything else speaking the
same shape — chat completions for `llm`, transcriptions for `stt`, speech for `tts`.
The key is named, never embedded: `api_key_env` says which environment variable to
read, and local servers that ignore keys need no variable at all.

Calls then report what your model actually produced, not just how long it took:
tokens per second for a model, characters per second for a voice, and for speech
generation a realtime factor — below 1 means it generates slower than it plays, which
a live call can never keep up with.

## Writing an adapter

The compiler validates `params` against the manifest and fills in defaults before
calling `create`, so an adapter only translates params into a Pipecat service:

```python
from pipecat.services.cartesia.tts import CartesiaTTSService

from vocalis.providers import language


def create(params, ctx):
    return CartesiaTTSService(
        api_key=ctx.secret("CARTESIA_API_KEY"),
        settings=CartesiaTTSService.Settings(
            voice=params["voice_id"],
            model=params["model"],
            language=language(params["language"]),
        ),
    )
```

`ctx.node` is the config node (LLM adapters pass `ctx.node.system_prompt` as the
system instruction); `ctx.secret(name)` reads an env var listed in the manifest.

Every manifest must pass the shared checks in `test_manifests.py`:
- it has an icon
- its defaults and examples are valid
- unknown params are rejected
- its env vars are listed in `.env.example`
