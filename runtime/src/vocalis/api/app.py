"""HTTP API for the dashboard: saved agents, their versions, and config validation.

The runtime owns the database so there is one implementation of the rules: /validate
runs the same checks as `vocalis run`, and nothing is stored that wouldn't compile.
"""

import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pipecat.transports.smallwebrtc.request_handler import SmallWebRTCRequest

from vocalis.api.schemas import (
    AgentCallStatsOut,
    AgentOut,
    AgentSummaryOut,
    CallIn,
    CallLogDetailOut,
    CallLogOut,
    CallOut,
    CallSummaryOut,
    ConfigIn,
    IssueOut,
    OverviewOut,
    ProviderOut,
    TemplateOut,
    ValidationOut,
    VersionOut,
)
from vocalis.calls import CallManager
from vocalis.compiler import validate
from vocalis.config import parse_config
from vocalis.issues import ConfigError
from vocalis.paths import REPO_ROOT
from vocalis.providers import ProviderRegistry
from vocalis.store import (
    AgentNotFound,
    AgentStore,
    CallStore,
    create_engine,
    create_session_factory,
)


def create_app(
    store: AgentStore | None = None, registry: ProviderRegistry | None = None
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.registry = registry or ProviderRegistry.from_directory()
        if store is not None:
            app.state.store = store
            app.state.call_store = None
            app.state.calls = CallManager(app.state.registry)
            try:
                yield
            finally:
                await app.state.calls.shutdown()
            return

        engine = create_engine()
        sessions = create_session_factory(engine)
        app.state.store = AgentStore(sessions)
        app.state.call_store = CallStore(sessions)
        app.state.calls = CallManager(app.state.registry, call_store=app.state.call_store)
        try:
            yield
        finally:
            await app.state.calls.shutdown()
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

    def get_calls(request: Request) -> CallManager:
        return request.app.state.calls

    def get_call_store(request: Request) -> CallStore:
        call_store = request.app.state.call_store
        if call_store is None:
            raise HTTPException(status_code=503, detail="call logs need a database")
        return call_store

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

    @app.get("/templates", response_model=list[TemplateOut])
    async def templates(registry: ProviderRegistry = Depends(get_registry)) -> list[TemplateOut]:
        """The example agents, offered as starting points for a new one."""
        found = []
        for path in sorted((REPO_ROOT / "examples").glob("*.json")):
            config = json.loads(path.read_text())
            needs = {
                name
                for node in config["nodes"]
                for spec in [registry.get(node["type"], node["provider"])]
                if spec
                for name in spec.env
            }
            found.append(
                TemplateOut(
                    id=path.stem,
                    name=config["name"],
                    description=config.get("description", ""),
                    needs_keys=sorted(needs),
                    config=config,
                )
            )
        return found

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

    @app.get("/calls", response_model=list[CallSummaryOut])
    async def list_calls(calls: CallManager = Depends(get_calls)) -> list[CallSummaryOut]:
        return [CallSummaryOut(**call.snapshot()) for call in calls.calls]

    @app.post("/calls", response_model=CallOut)
    async def start_call(
        body: CallIn,
        calls: CallManager = Depends(get_calls),
        store: AgentStore = Depends(get_store),
        registry: ProviderRegistry = Depends(get_registry),
    ) -> CallOut:
        """Answer a browser's offer and put the agent on the line.

        Takes either a saved agent's slug or a config straight from the canvas, so an
        agent can be called before it has ever been saved.
        """
        version = None
        if body.config is not None:
            raw = body.config
        elif body.slug:
            saved = await found(store.get(body.slug))
            raw, version = saved.config, saved.version
        else:
            raise HTTPException(status_code=422, detail="pass either slug or config")

        check(raw, registry)
        answer = await calls.start(
            parse_config(raw),
            SmallWebRTCRequest(
                sdp=body.sdp, type=body.type, pc_id=body.pc_id, restart_pc=body.restart_pc
            ),
            slug=body.slug,
            version=version,
            raw_config=raw,
        )
        if not answer:
            raise HTTPException(status_code=503, detail="could not establish the call")
        return CallOut(**answer)

    @app.get("/calls/{call_id}/events")
    async def call_events(call_id: str, calls: CallManager = Depends(get_calls)) -> Response:
        """Transcript and per-turn latency as they happen, as server-sent events."""
        call = calls.get(call_id)
        if call is None:
            raise HTTPException(status_code=404, detail=f"no call {call_id}")

        async def stream():
            async for event in call.watch():
                yield f"data: {json.dumps(event)}\n\n"

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
        )

    @app.get("/stats", response_model=OverviewOut)
    async def overview(days: int = 14, logs: CallStore = Depends(get_call_store)) -> OverviewOut:
        stats = await logs.overview(days=days)
        return OverviewOut(
            **{key: value for key, value in vars(stats).items() if key != "recent"},
            recent=[CallLogOut(**vars(call)) for call in stats.recent],
        )

    @app.get("/logs", response_model=list[CallLogOut])
    async def list_logs(
        agent: str | None = None,
        limit: int = 50,
        logs: CallStore = Depends(get_call_store),
    ) -> list[CallLogOut]:
        return [CallLogOut(**vars(call)) for call in await logs.list(slug=agent, limit=limit)]

    @app.get("/logs/{log_id}", response_model=CallLogDetailOut)
    async def get_log(log_id: str, logs: CallStore = Depends(get_call_store)) -> CallLogDetailOut:
        detail = await logs.get(log_id)
        if detail is None:
            raise HTTPException(status_code=404, detail=f"no call {log_id}")
        return CallLogDetailOut(
            call=CallLogOut(**vars(detail.summary)),
            config=detail.config,
            turns=detail.turns,
            messages=detail.messages,
        )

    @app.delete("/logs/{log_id}", status_code=204)
    async def delete_log(log_id: str, logs: CallStore = Depends(get_call_store)) -> None:
        if not await logs.delete(log_id):
            raise HTTPException(status_code=404, detail=f"no call {log_id}")

    @app.get("/agents/{slug}/calls", response_model=AgentCallStatsOut)
    async def agent_call_stats(
        slug: str, logs: CallStore = Depends(get_call_store)
    ) -> AgentCallStatsOut:
        return AgentCallStatsOut(**await logs.stats(slug))

    @app.post("/calls/{call_id}/hangup", status_code=204)
    async def hangup(call_id: str, calls: CallManager = Depends(get_calls)) -> None:
        if not await calls.hangup(call_id):
            raise HTTPException(status_code=404, detail=f"no call {call_id}")

    return app


async def found[T](awaitable) -> T:
    """Turn a missing agent or version into a 404."""
    try:
        return await awaitable
    except AgentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


app = create_app()
