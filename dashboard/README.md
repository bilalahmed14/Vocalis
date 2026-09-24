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

| Path                  | What it does                                            |
| --------------------- | -------------------------------------------------------- |
| `app/page.tsx`        | Saved agents                                             |
| `app/agents/[slug]/`  | The canvas for one saved agent, with its version history |
| `app/api/[...path]/`  | Proxy to the runtime API                                 |
| `components/canvas/`  | Editor, custom node, palette, inspector, params form, toolbar |
| `lib/api.ts`          | Typed client for the runtime API                         |
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

The runtime needs UDP for WebRTC, so run it on the host while developing:

```bash
docker compose -f ../deploy/docker-compose.yml up -d postgres
uv run uvicorn vocalis.api.app:app --port 8000
```

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
