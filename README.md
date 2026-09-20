# Vocalis

Open-source visual voice agent builder. Patch STT, LLM and TTS providers together
like cables on an audio patchbay, test calls in the browser, and see live latency
per node. Built on [Pipecat](https://github.com/pipecat-ai/pipecat). Self-hostable
with one command.

> **Status:** early development. Phase 1 (engine and CLI) is done, and the canvas can
> build and export agents. Test calls and live metrics are next.

## Principles

- **The agent config (JSON) is the core contract.** The canvas edits it, the runtime
  executes it, and the CLI runs it without the UI.
- **Every node shows live metrics.** Nothing is a black box.
- **Providers are plugins.** Adding one means one Python file plus one JSON schema.

## Repo layout

| Path         | What lives there                                               |
| ------------ | -------------------------------------------------------------- |
| `runtime/`   | Pipecat worker and HTTP API: configs, pipelines, saved agents    |
| `dashboard/` | Next.js canvas and test-call UI                                |
| `schema/`    | JSON Schema for agent configs (source of truth, shared by both) |
| `providers/` | Provider plugins (Python adapter + node schema + icon)         |
| `cli/`       | `vocalis run agent.json`                                       |
| `deploy/`    | `docker-compose.yml`                                           |

## Stack

- **Runtime:** Python 3.12, Pipecat, FastAPI, SmallWebRTC transport
- **Dashboard:** Next.js (App Router), TypeScript, React Flow, Tailwind, shadcn/ui
- **Storage:** Postgres (agents, versions, call logs), Redis (live metrics pub/sub)
- **Dev:** Docker Compose, uv, pnpm, pytest, Playwright

## Roadmap

1. **Engine:** config schema, pipeline compiler, providers, CLI
2. **Canvas:** React Flow editor with typed ports and schema-driven forms
3. **Test call + live metrics:** browser WebRTC calls with per-node latency
4. **Hot-swap:** replace a provider mid-call at the next turn boundary
5. **Audio lab nodes:** noise suppression, VAD tuning, gain, scopes
6. **Ship:** `docker compose up`, examples, contributor guide, CI

## Quickstart

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env      # add keys for the providers your agent uses
uv run vocalis run examples/basic.json
```

`examples/basic.json` uses Deepgram, OpenAI and Cartesia, so it needs those three
keys. Speak into your mic (headphones recommended) and press Ctrl+C to hang up. API
keys are only ever read from the environment, never from agent configs.

Other commands: `vocalis validate <agent.json>`, `vocalis providers`,
`vocalis devices`. See [cli/README.md](cli/README.md).

## Run the whole thing

```bash
docker compose -f deploy/docker-compose.yml up -d --build
```

One command brings up the canvas, the API and Postgres, migrations included. Open
[localhost:3000](http://localhost:3000): drag providers from the palette, patch them
together (only matching ports connect), edit each node in the inspector, and save. You
need API keys only to place a call. See [deploy/README.md](deploy/README.md).

To work on the canvas itself, run it from source against the same API:

```bash
docker compose -f deploy/docker-compose.yml up -d postgres api
pnpm --dir dashboard install && pnpm --dir dashboard dev
```

## Providers

| Stage | Providers                                  |
| ----- | ------------------------------------------ |
| VAD   | Silero (local)                             |
| STT   | Deepgram, Whisper (local, `uv sync --extra whisper`) |
| LLM   | OpenAI (and OpenAI-compatible), Anthropic, Groq |
| TTS   | ElevenLabs, Cartesia                       |

Adding one takes a folder with a manifest, an adapter and an icon; see
[providers/README.md](providers/README.md).

## Development

```bash
uv sync --all-extras              # Python workspace, including local Whisper
uv run pytest                     # runtime, provider and CLI tests
uv run ruff check .               # lint
uv run schema/validate.py         # check examples against the schema

docker compose -f deploy/docker-compose.yml up -d postgres   # database tests need this

pnpm --dir dashboard install
pnpm --dir dashboard test         # canvas tests
pnpm --dir dashboard gen:schema   # regenerate TS types after a schema change
```

## License

[MIT](LICENSE)
