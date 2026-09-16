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
| llm  | openai     | `OPENAI_API_KEY`       |
| llm  | anthropic  | `ANTHROPIC_API_KEY`    |
| llm  | groq       | `GROQ_API_KEY`         |
| tts  | elevenlabs | `ELEVENLABS_API_KEY`   |
| tts  | cartesia   | `CARTESIA_API_KEY`     |

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
