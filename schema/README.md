# Agent config schema

`agent.v1.schema.json` defines the agent config: the JSON contract shared by the
canvas, the runtime and the CLI. It is the single source of truth. TypeScript types
for the dashboard are generated from it, never written by hand.

## Shape

```jsonc
{
  "schema_version": 1,
  "name": "Basic assistant",
  "nodes": [
    { "id": "vad", "type": "vad", "provider": "silero", "params": {} },
    { "id": "stt", "type": "stt", "provider": "deepgram", "params": { "model": "nova-3" } },
    { "id": "llm", "type": "llm", "provider": "openai", "system_prompt": "...", "params": {} },
    { "id": "tts", "type": "tts", "provider": "cartesia", "params": { "voice_id": "..." } }
  ],
  "edges": [
    { "source": "vad", "target": "stt" },
    { "source": "stt", "target": "llm" },
    { "source": "llm", "target": "tts" }
  ]
}
```

See [`examples/basic.json`](../examples/basic.json) for a complete config.

## Node types and ports

Every node has one input and one output. Port types come from the node type (the
`x-ports` annotation on each node definition), so an edge is only valid when the
source's output type matches the target's input type.

| Type  | Input | Output | Notes                                  |
| ----- | ----- | ------ | -------------------------------------- |
| `vad` | audio | audio  | Marks where the user starts and stops speaking |
| `stt` | audio | text   |                                        |
| `llm` | text  | text   | Requires `system_prompt`               |
| `tts` | text  | audio  |                                        |

The pipeline's first node receives audio from the transport (local mic in the CLI,
WebRTC in the browser) and its last node plays audio back. The config doesn't name
the transport, so the same file runs everywhere.

## What the schema checks and what the compiler checks

The schema checks structure: required fields, node types, id formats, no unknown keys.

The runtime compiler checks what JSON Schema can't:

- node ids are unique
- edges reference existing nodes
- edge port types match (audio to audio, text to text)
- the nodes form a single chain, `[vad ->] stt -> llm -> tts` in v1
- the provider exists and supports the node type
- `params` match the provider's own schema
- the provider's environment variables are set (at compile time only)

## Providers and secrets

`provider` names a plugin in [`/providers`](../providers). Each plugin has a
`provider.json` manifest, validated by `provider.v1.schema.json`, that holds its
display name, required environment variables and the JSON Schema for `params`. API keys never go in a config; providers read them from
the environment (see `.env.example`).

## Versioning

`schema_version` changes only for breaking changes, and the file name changes with
it (`agent.v2.schema.json`). Adding an optional field is not a breaking change.
