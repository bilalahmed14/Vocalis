# Patchbay

Open-source visual voice agent builder. Patch STT, LLM and TTS providers together
like cables on an audio patchbay, test calls in the browser, and see live latency
per node. Built on [Pipecat](https://github.com/pipecat-ai/pipecat). Self-hostable
with one command.

> **Status:** early development. Phase 1 (engine, no UI) is in progress.

## Principles

- **The agent config (JSON) is the core contract.** The canvas edits it, the runtime
  executes it, and the CLI runs it without the UI.
- **Every node shows live metrics.** Nothing is a black box.
- **Providers are plugins.** Adding one means one Python file plus one JSON schema.

## Repo layout

| Path         | What lives there                                               |
| ------------ | -------------------------------------------------------------- |
| `runtime/`   | Pipecat worker: loads a config, builds the pipeline, streams metrics |
| `dashboard/` | Next.js canvas and test-call UI                                |
| `schema/`    | JSON Schema for agent configs (source of truth, shared by both) |
| `providers/` | Provider plugins (Python adapter + node schema + icon)         |
| `cli/`       | `patchbay run agent.json`                                      |
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

## Configuration

API keys are read from environment variables, never from agent configs.
Copy the template and fill in the providers you use:

```bash
cp .env.example .env
```

## License

[MIT](LICENSE)
