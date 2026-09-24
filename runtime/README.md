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
| `store/`       | Postgres tables and the agent/version store                      |
| `tracing/`     | Per-turn latency, mapped onto the agent's nodes                  |
| `api/`         | FastAPI app the dashboard talks to                               |

## The API

```bash
docker compose -f deploy/docker-compose.yml up -d --build   # Postgres + the API
```

| Method | Path | Does |
| ------ | ---- | ---- |
| `GET` | `/providers` | installed provider plugins, with their params schemas |
| `POST` | `/validate` | check a config; returns node-level issues, saves nothing |
| `GET`/`POST` | `/agents` | list agents, or save a new one |
| `GET`/`PUT`/`DELETE` | `/agents/{slug}` | read, save a new version, or delete |
| `GET` | `/agents/{slug}/versions` | version history |
| `GET` | `/agents/{slug}/versions/{n}` | one old config |
| `POST` | `/agents/{slug}/versions/{n}/restore` | copy an old version forward |

Saving runs the same checks as `vocalis run`, so the database only ever holds configs
that compile; an invalid one comes back as a 422 listing the nodes at fault. Versions
are immutable, and restoring writes a new version rather than rewinding history.

## Tracing

```python
tracer = CallTracer(agent)
worker = PipelineWorker(agent.pipeline(transport), observers=tracer.observers, ...)
# ...after the call
tracer.call.percentile(0.5)      # median time to first audio
tracer.call.slowest_stages()     # what to fix first
```

Pipecat measures where a turn's time goes; the tracer maps each measurement back to
the node that owns it, so a slow stage names a box on the canvas. Time no service
owns is kept as its own stage rather than dropped, because that is usually where the
latency actually is.

## Tests

From the repo root:

```bash
uv run pytest                                                 # database tests skip
DATABASE_URL=postgresql://vocalis:vocalis@localhost:5432/vocalis uv run pytest
```
