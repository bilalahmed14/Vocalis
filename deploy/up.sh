#!/usr/bin/env bash
#
# Bring up a Vocalis stack that can place calls.
#
# Postgres and the canvas run in containers. The runtime runs on your machine,
# because a browser call carries its audio over UDP and Docker forwards only TCP:
# in a container the call connects, the transcript appears, and no voice ever
# arrives. Everything else about the container stack is fine, so only the runtime
# moves out.
#
#   ./deploy/up.sh                                  # localhost:3000
#   VOCALIS_DASHBOARD_PORT=3010 ./deploy/up.sh      # somewhere else
#
# Ctrl+C stops the runtime. Postgres and the canvas keep running:
#   docker compose -f deploy/docker-compose.yml down
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT="$PWD"

API_PORT="${VOCALIS_API_PORT:-8000}"
DASHBOARD_PORT="${VOCALIS_DASHBOARD_PORT:-3000}"
DB_PORT="${VOCALIS_DB_PORT:-5432}"

for tool in docker uv; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "vocalis: $tool is not installed." >&2
    case "$tool" in
      docker) echo "  Docker Desktop, Colima and OrbStack all work: https://docs.docker.com/get-started/" >&2 ;;
      uv) echo "  Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2 ;;
    esac
    exit 1
  fi
done

# The canvas proxies the browser to the runtime, so it needs the host's address
# rather than a name on the compose network.
export VOCALIS_API_URL="http://host.docker.internal:${API_PORT}"

echo "vocalis: starting Postgres and the canvas…"
docker compose -f deploy/docker-compose.yml up -d --build postgres dashboard

# Provider keys are optional: the runtime starts without them and only placing a
# call needs them, so a missing .env is not an error. The path is absolute because
# migrations run from runtime/, and `${a[@]+...}` is for the bash 3.2 on macOS,
# where expanding an empty array trips `set -u`.
env_args=()
if [ -f "$ROOT/.env" ]; then
  env_args=(--env-file "$ROOT/.env")
fi

export DATABASE_URL="postgresql://vocalis:vocalis@localhost:${DB_PORT}/vocalis"

echo "vocalis: applying migrations…"
(cd runtime && uv run ${env_args[@]+"${env_args[@]}"} alembic upgrade head)

cat <<EOF

  canvas    http://localhost:${DASHBOARD_PORT}
  runtime   http://localhost:${API_PORT}/docs
  database  localhost:${DB_PORT}

  Open the canvas, pick an agent and press Test call. Ctrl+C stops the runtime.

EOF

# 0.0.0.0, not localhost: the canvas container reaches the runtime from outside.
exec uv run ${env_args[@]+"${env_args[@]}"} uvicorn vocalis.api.app:app --host 0.0.0.0 --port "$API_PORT"
