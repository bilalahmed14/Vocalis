# Running Vocalis with Docker

```bash
./deploy/up.sh
```

That brings up Postgres, the canvas and the Vocalis runtime, and applies database
migrations on start, so a fresh machine needs nothing else:

- the canvas at [localhost:3000](http://localhost:3000)
- the runtime at [localhost:8000/docs](http://localhost:8000/docs)

Ctrl+C stops the runtime; Postgres and the canvas keep running until you bring them
down. Provider API keys are only needed to place a call; building and saving agents
works without them.

Any Docker works: Docker Desktop, Colima, OrbStack, or Docker Engine on Linux. The
script also needs [uv](https://docs.astral.sh/uv/), which runs the runtime.

## Why the runtime isn't in a container

A browser call carries its audio over **UDP**, and Docker's published ports are TCP.
From a container the signalling works perfectly — the call connects, the transcript
streams, the latency is recorded — and not one millisecond of voice arrives. On
macOS and Windows there is no way around it either, because the container sits behind
a virtual machine that forwards TCP only.

So `up.sh` splits the stack where the problem is: Postgres and the canvas stay in
containers, the runtime runs on your machine, and the canvas is told where to find it
through `VOCALIS_API_URL`. Media then goes straight from the browser to a process on
the same machine, which is the one path that always works.

The all-container stack is still there and still useful — building agents, versions,
call logs, anything that isn't a live call:

```bash
docker compose -f deploy/docker-compose.yml up -d --build
```

## What runs

| Service     | Port | What it is                                              |
| ----------- | ---- | ------------------------------------------------------- |
| `postgres`  | 5432 | Saved agents and their version history                  |
| `api`       | 8000 | FastAPI: agents, versions, config validation, providers |
| `dashboard` | 3000 | The canvas (Next.js), which proxies browser calls to the API |

The browser only ever talks to the dashboard, which forwards to the API over the
compose network. Nothing else has to be reachable from outside, and there is no CORS
setup or public API URL to configure.

The API image carries `/schema` and `/providers`, so the providers it offers are the
plugins in this repo — add one and rebuild.

## Configuration

| Variable               | Default                  | What it does                        |
| ---------------------- | ------------------------ | ----------------------------------- |
| `VOCALIS_API_PORT`       | `8000`                  | Host port for the API             |
| `VOCALIS_DASHBOARD_PORT` | `3000`                  | Host port for the canvas          |
| `VOCALIS_DB_PORT`        | `5432`                  | Host port for Postgres            |
| `DATABASE_URL`         | the compose `postgres`   | Where the API stores agents         |
| `VOCALIS_CORS_ORIGINS` | `http://localhost:3000`  | Who may call the API from a browser |
| `VOCALIS_API_URL`      | the compose `api`        | Where the canvas looks for the runtime |

If a port is already taken on your machine, override it for the run:

```bash
VOCALIS_API_PORT=8010 VOCALIS_DASHBOARD_PORT=3010 ./deploy/up.sh
```

Provider API keys come from `.env` at the repo root (copy `.env.example`). The file is
optional: the API runs without it, and only starting a call needs the keys.

## Everyday commands

```bash
docker compose -f deploy/docker-compose.yml logs -f api   # follow the API log
docker compose -f deploy/docker-compose.yml down          # stop, keep the data
docker compose -f deploy/docker-compose.yml down -v       # stop and wipe the database
docker compose -f deploy/docker-compose.yml exec postgres psql -U vocalis vocalis
```

Agents live in the `vocalis-db` volume, so they survive `down` and restarts.

## Running the database only

Working on the Python code but want a real database for the tests:

```bash
docker compose -f deploy/docker-compose.yml up -d postgres
DATABASE_URL=postgresql://vocalis:vocalis@localhost:5432/vocalis uv run pytest
```

Without a database those tests skip rather than fail, so the suite still passes on a
machine with no Docker.

## Migrations

Migrations live in `runtime/migrations` and run automatically when the API container
starts. To run them by hand:

```bash
cd runtime && DATABASE_URL=postgresql://vocalis:vocalis@localhost:5432/vocalis uv run alembic upgrade head
```

A test compares the migrations against the ORM models, so the two can't drift apart.
