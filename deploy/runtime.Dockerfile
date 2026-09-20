# The Vocalis runtime: the HTTP API the dashboard and CLI talk to.
# Build from the repo root: docker build -f deploy/runtime.Dockerfile .
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, so editing source doesn't reinstall the world.
COPY pyproject.toml uv.lock README.md ./
COPY runtime/pyproject.toml runtime/README.md runtime/
RUN uv sync --frozen --no-dev --package vocalis-runtime --no-install-workspace

# The schema and provider plugins are read at runtime, not bundled into the package.
COPY schema/ schema/
COPY providers/ providers/
COPY examples/ examples/
COPY runtime/ runtime/
RUN uv sync --frozen --no-dev --package vocalis-runtime

ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app/runtime
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"

# Migrations run on start, so a fresh database needs no extra step.
CMD ["sh", "-c", "alembic upgrade head && uvicorn vocalis.api.app:app --host 0.0.0.0 --port 8000"]
