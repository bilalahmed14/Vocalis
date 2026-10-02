# Vocalis dashboard

The canvas: patch provider nodes together, edit their settings, save them, and export
the agent config the runtime and CLI run.

```bash
docker compose -f ../deploy/docker-compose.yml up -d postgres api   # the backend
pnpm install
pnpm dev          # http://localhost:3000
pnpm test         # round-trip, validation and API client tests
pnpm gen:schema   # regenerate types after changing /schema
```

Set `VOCALIS_API_URL` if the runtime isn't on `http://localhost:8000`.

## How it stays in sync with the rest of the repo

- **Types come from `/schema`.** `pnpm gen:schema` copies the JSON Schemas into
  `lib/schema/` and generates `agent.gen.ts` and `provider.gen.ts` from them. Nothing
  here hand-writes a type that the schema already describes.
- **Port types come from the schema too.** Each node definition carries `x-ports`, so
  the canvas refuses the same cables the Python compiler would: audio only feeds
  audio, text only feeds text.
- **The palette and the node forms come from the providers the runtime reports.**
  Every provider's `provider.json` supplies its name, icon, required keys and a JSON
  Schema for its settings, which the inspector renders as a form. Adding a provider
  needs no change here.
- **Saved agents live in the runtime's database**, reached through its HTTP API. The
  browser only talks to this app: `/api/*` proxies to the runtime, so there's no CORS
  configuration and no public API URL.

## Layout

| Path                          | What it does                                          |
| ----------------------------- | ------------------------------------------------------ |
| `app/page.tsx`                | Saved agents                                           |
| `app/new/`                    | Start from a template or an empty canvas               |
| `app/agents/[slug]/`          | One agent: Pipeline, Calls and Settings tabs           |
| `app/calls/`                  | Every call, and one call's turns and transcript        |
| `app/api/[...path]/`          | Proxy to the runtime API                               |
| `components/canvas/`          | Editor, custom node, palette, inspector, toolbar       |
| `components/calls/`           | Call table, waterfall, stat tiles                      |
| `lib/api.ts`                  | Typed client for the runtime API                       |
| `lib/agent/flow.ts`   | Config to canvas graph and back, in pipeline order       |
| `lib/agent/config.ts` | Canonical JSON export                                    |
| `lib/agent/validate.ts` | Canvas-side checks while editing                       |
| `lib/providers.ts`    | Reads the provider plugins from `/providers`             |

## Test calls

**Test call** places a WebRTC call from the browser to the runtime: your microphone
goes in, the agent's voice comes back, and the transcript and per-turn latency stream
in beside the canvas as it happens. Each node shows what it cost on the last turn, and
the panel breaks the turn down stage by stage — including the time no service owns.

An agent can be called before it's ever saved: the canvas sends the config it has.

The runtime needs UDP for WebRTC, so run it on the host while developing. Nothing
loads `.env` for you, and a provider without its key refuses the call:

```bash
docker compose -f ../deploy/docker-compose.yml up -d postgres
uv run --env-file ../.env uvicorn vocalis.api.app:app --port 8000
```

### Hearing the agent

The voice arrives on the same peer connection and plays through an audio element in
the page. Two things make that fail quietly, so the panel reports both:

- **A browser that won't start audio on its own.** `autoplay` is a request, not a
  guarantee; Safari and a Chrome without autoplay permission reject it, and the
  rejected promise is the only notice. The header then offers **Let the agent be
  heard**, which starts playback from your click.
- **A meter next to the status**, showing the agent's voice as it arrives. Flat while
  the transcript fills in means the audio never reached the browser. Moving while you
  hear nothing means it did, and the output device or its volume is what's swallowing
  it — worth checking first if you muted your speakers to stop the agent interrupting
  itself.

## Call logs

Every test call is written down: the config exactly as it ran, each turn's stages,
and the transcript. The **Calls** tab on an agent shows its history with headline
numbers; a call's page shows every turn's waterfall next to what was said.

The config is stored per call on purpose — an agent gets edited between calls, and
comparing two runs is meaningless without knowing what each one actually used.

## Saving and versions

Save writes a new version through the API; the dropdown lists the history, and picking
an old one loads it onto the canvas, with Restore to bring it back as the newest
version. Nothing is ever overwritten.

## Validation

The canvas reports problems as you edit: unknown providers, settings that don't match
a provider's schema, missing system prompts, nodes that aren't patched in, and a chain
that doesn't start and end with audio. Those checks are instant but advisory — the
runtime compiler is the authority, and it runs again on every save, so an invalid
agent is refused with the same node-level messages `vocalis run` would print.

## Export

`Export JSON` writes the same bytes a hand-written config would have: fields in schema
order, 2-space JSON. A test loads `examples/basic.json`, round-trips it through the
canvas and asserts the output is identical.
