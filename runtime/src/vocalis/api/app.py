"""HTTP API for the dashboard: saved agents, their versions, and config validation.

The runtime owns the database so there is one implementation of the rules: /validate
runs the same checks as `vocalis run`, and nothing is stored that wouldn't compile.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from vocalis.api.schemas import (
    AgentOut,
    AgentSummaryOut,
    ConfigIn,
    IssueOut,
    ProviderOut,
    ValidationOut,
    VersionOut,
)
from vocalis.compiler import validate
from vocalis.config import parse_config
from vocalis.issues import ConfigError
from vocalis.providers import ProviderRegistry
from vocalis.store import AgentNotFound, AgentStore, create_engine, create_session_factory


def create_app(
    store: AgentStore | None = None, registry: ProviderRegistry | None = None
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.registry = registry or ProviderRegistry.from_directory()
        if store is not None:
            app.state.store = store
            yield
            return

        engine = create_engine()
        app.state.store = AgentStore(create_session_factory(engine))
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="Vocalis", version="0.1.0", lifespan=lifespan)

    origins = os.environ.get("VOCALIS_CORS_ORIGINS", "http://localhost:3000")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_store(request: Request) -> AgentStore:
        return request.app.state.store

    def get_registry(request: Request) -> ProviderRegistry:
        return request.app.state.registry

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/providers", response_model=list[ProviderOut])
    async def providers(registry: ProviderRegistry = Depends(get_registry)) -> list[ProviderOut]:
        return [
            ProviderOut(
                id=spec.id,
                type=spec.type,
                name=spec.name,
                description=spec.description,
                docs_url=spec.docs_url,
                env=list(spec.env),
                needs_vad=spec.needs_vad,
                params=dict(spec.params_schema),
                icon=(spec.path / "icon.svg").read_text()
                if (spec.path / "icon.svg").is_file()
                else None,
            )
            for spec in registry
        ]

    @app.post("/validate", response_model=ValidationOut)
    async def validate_config(
        body: ConfigIn, registry: ProviderRegistry = Depends(get_registry)
    ) -> ValidationOut:
        """Check a config without saving it. Never raises: the issues are the answer."""
        try:
            issues = validate(parse_config(body.config), registry)
        except ConfigError as e:
            issues = e.issues
        return ValidationOut(valid=not issues, issues=[IssueOut.of(issue) for issue in issues])

    def check(config: dict, registry: ProviderRegistry) -> None:
        try:
            issues = validate(parse_config(config), registry)
        except ConfigError as e:
            issues = e.issues
        if issues:
            raise HTTPException(
                status_code=422,
                detail={"issues": [IssueOut.of(issue).model_dump() for issue in issues]},
            )

    @app.get("/agents", response_model=list[AgentSummaryOut])
    async def list_agents(store: AgentStore = Depends(get_store)) -> list[AgentSummaryOut]:
        return [AgentSummaryOut(**vars(summary)) for summary in await store.list_agents()]

    @app.post("/agents", response_model=AgentOut, status_code=201)
    async def create_agent(
        body: ConfigIn,
        store: AgentStore = Depends(get_store),
        registry: ProviderRegistry = Depends(get_registry),
    ) -> AgentOut:
        check(body.config, registry)
        return AgentOut(**vars(await store.create(body.config, body.note)))

    @app.get("/agents/{slug}", response_model=AgentOut)
    async def get_agent(slug: str, store: AgentStore = Depends(get_store)) -> AgentOut:
        return AgentOut(**vars(await found(store.get(slug))))

    @app.put("/agents/{slug}", response_model=AgentOut)
    async def save_agent(
        slug: str,
        body: ConfigIn,
        store: AgentStore = Depends(get_store),
        registry: ProviderRegistry = Depends(get_registry),
    ) -> AgentOut:
        check(body.config, registry)
        return AgentOut(**vars(await found(store.save(slug, body.config, body.note))))

    @app.delete("/agents/{slug}", status_code=204)
    async def delete_agent(slug: str, store: AgentStore = Depends(get_store)) -> None:
        await found(store.delete(slug))

    @app.get("/agents/{slug}/versions", response_model=list[VersionOut])
    async def agent_versions(slug: str, store: AgentStore = Depends(get_store)) -> list[VersionOut]:
        return [VersionOut(**vars(v)) for v in await found(store.versions(slug))]

    @app.get("/agents/{slug}/versions/{version}", response_model=AgentOut)
    async def agent_version(
        slug: str, version: int, store: AgentStore = Depends(get_store)
    ) -> AgentOut:
        return AgentOut(**vars(await found(store.version(slug, version))))

    @app.post("/agents/{slug}/versions/{version}/restore", response_model=AgentOut)
    async def restore_version(
        slug: str, version: int, store: AgentStore = Depends(get_store)
    ) -> AgentOut:
        return AgentOut(**vars(await found(store.restore(slug, version))))

    return app


async def found[T](awaitable) -> T:
    """Turn a missing agent or version into a 404."""
    try:
        return await awaitable
    except AgentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


app = create_app()
