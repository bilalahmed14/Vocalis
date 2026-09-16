# vocalis-runtime

Loads an agent config, validates it, and compiles it into a Pipecat pipeline.

```python
from vocalis import compile_agent, load_config

config = load_config("examples/basic.json")  # JSON Schema checks
agent = compile_agent(config)  # graph, providers, params, secrets
pipeline = agent.pipeline(transport)  # any Pipecat transport
```

Every problem is reported as an `Issue` that names the node (or edge) at fault, so
the CLI can print it and the canvas can highlight it:

```
examples/broken.json: invalid agent config (4 problems)
  - node "llm": "vad" outputs audio but "llm" takes text input
  - node "vad": has more than one outgoing cable
  - node "stt": params: unknown field "api_key"
  - node "tts": unknown tts provider "elevenlab" (available: cartesia)
```

## Modules

| Module         | Job                                                              |
| -------------- | ---------------------------------------------------------------- |
| `schema.py`    | Loads `/schema`, turns JSON Schema errors into node-level issues |
| `config.py`    | Typed view of a config (`AgentConfig`, `Node`, `Edge`)           |
| `graph.py`     | Port types, single-chain shape, node order                       |
| `providers.py` | Discovers plugins in `/providers`, validates params, loads adapters |
| `compiler.py`  | Runs all checks, builds processors, wires the `Pipeline`         |

## Tests

From the repo root:

```bash
uv run pytest
```
