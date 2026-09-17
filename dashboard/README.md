# Vocalis dashboard

The canvas: patch provider nodes together, edit their settings, and export the agent
config the runtime and CLI run.

```bash
pnpm install
pnpm dev          # http://localhost:3000
pnpm test         # round-trip and validation tests
pnpm gen:schema   # regenerate types after changing /schema
```

## How it stays in sync with the rest of the repo

- **Types come from `/schema`.** `pnpm gen:schema` copies the JSON Schemas into
  `lib/schema/` and generates `agent.gen.ts` and `provider.gen.ts` from them. Nothing
  here hand-writes a type that the schema already describes.
- **Port types come from the schema too.** Each node definition carries `x-ports`, so
  the canvas refuses the same cables the Python compiler would: audio only feeds
  audio, text only feeds text.
- **The palette and the node forms come from `/providers`.** Every provider's
  `provider.json` supplies its name, icon, required keys and a JSON Schema for its
  settings, which the inspector renders as a form. Adding a provider needs no change
  here.

## Layout

| Path                  | What it does                                            |
| --------------------- | -------------------------------------------------------- |
| `app/page.tsx`        | Reads providers and the starting agent, renders the editor |
| `components/canvas/`  | Editor, custom node, palette, inspector, params form     |
| `lib/agent/flow.ts`   | Config to canvas graph and back, in pipeline order       |
| `lib/agent/config.ts` | Canonical JSON export                                    |
| `lib/agent/validate.ts` | Canvas-side checks while editing                       |
| `lib/providers.ts`    | Reads the provider plugins from `/providers`             |

## Validation

The canvas reports problems as you edit: unknown providers, settings that don't match
a provider's schema, missing system prompts, nodes that aren't patched in, and a chain
that doesn't start and end with audio. The runtime compiler stays the authority — it
also checks API keys and actually builds the pipeline — so `vocalis validate` is the
final word before a call.

## Export

`Export JSON` writes the same bytes a hand-written config would have: fields in schema
order, 2-space JSON. A test loads `examples/basic.json`, round-trips it through the
canvas and asserts the output is identical.
