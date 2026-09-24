"""The HTTP API the dashboard talks to."""

import copy

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from helpers import VALID_CONFIG
from vocalis import ProviderRegistry
from vocalis.api import create_app


@pytest_asyncio.fixture
async def client(store, registry):
    app = create_app(store=store, registry=registry)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://runtime") as client:
            yield client


@pytest.fixture
def agent_config():
    return copy.deepcopy(VALID_CONFIG) | {"name": "Support bot"}


async def test_healthz(client):
    assert (await client.get("/healthz")).json() == {"status": "ok"}


async def test_create_and_read_an_agent(client, agent_config):
    created = (await client.post("/agents", json={"config": agent_config})).json()

    assert created["slug"] == "support-bot"
    assert created["version"] == 1

    fetched = (await client.get("/agents/support-bot")).json()
    assert fetched["config"] == agent_config


async def test_saving_creates_a_version_and_restoring_moves_forward(client, agent_config):
    await client.post("/agents", json={"config": agent_config})
    updated = agent_config | {"description": "second"}

    saved = await client.put("/agents/support-bot", json={"config": updated, "note": "tweak"})
    assert saved.json()["version"] == 2

    versions = (await client.get("/agents/support-bot/versions")).json()
    assert [(v["version"], v["note"]) for v in versions] == [(2, "tweak"), (1, None)]

    restored = (await client.post("/agents/support-bot/versions/1/restore")).json()
    assert restored["version"] == 3
    assert "description" not in restored["config"]


async def test_listing_agents(client, agent_config):
    await client.post("/agents", json={"config": agent_config})

    listed = (await client.get("/agents")).json()

    assert [(a["slug"], a["version"]) for a in listed] == [("support-bot", 1)]


async def test_invalid_configs_are_refused_with_node_level_issues(client, agent_config):
    agent_config["nodes"][2]["provider"] = "gpt"

    response = await client.post("/agents", json={"config": agent_config})

    assert response.status_code == 422
    assert response.json()["detail"]["issues"][0] == {
        "message": 'node "llm": unknown llm provider "gpt" (available: fake, other)',
        "node_id": "llm",
        "node_index": 2,
        "edge_index": None,
        "path": "/nodes/2/provider",
    }
    assert (await client.get("/agents")).json() == []


async def test_validate_reports_issues_without_saving(client, agent_config):
    del agent_config["nodes"][2]["system_prompt"]

    response = await client.post("/validate", json={"config": agent_config})

    assert response.json() == {
        "valid": False,
        "issues": [
            {
                "message": 'node "llm": missing required field "system_prompt"',
                "node_id": "llm",
                "node_index": 2,
                "edge_index": None,
                "path": "/nodes/2",
            }
        ],
    }
    assert (await client.get("/agents")).json() == []


async def test_validate_accepts_a_good_config(client, agent_config):
    assert (await client.post("/validate", json={"config": agent_config})).json() == {
        "valid": True,
        "issues": [],
    }


async def test_providers_lists_the_installed_plugins(client):
    listed = (await client.get("/providers")).json()

    assert {(p["type"], p["id"]) for p in listed} == {
        ("vad", "fake"),
        ("stt", "fake"),
        ("llm", "fake"),
        ("llm", "other"),
        ("tts", "fake"),
    }
    assert listed[0]["params"]["type"] == "object"


async def test_real_providers_are_served_with_icons():
    app = create_app(store=None, registry=ProviderRegistry.from_directory())
    app.state.registry = ProviderRegistry.from_directory()
    app.state.store = None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://runtime") as client:
        listed = (await client.get("/providers")).json()

    deepgram = next(p for p in listed if p["id"] == "deepgram")
    assert deepgram["env"] == ["DEEPGRAM_API_KEY"]
    assert deepgram["icon"].startswith("<svg")


async def test_unknown_agent_is_a_404(client):
    assert (await client.get("/agents/nope")).status_code == 404
    assert (await client.put("/agents/nope", json={"config": VALID_CONFIG})).status_code == 404


async def test_starting_a_call_needs_a_slug_or_a_config(client):
    response = await client.post("/calls", json={"sdp": "v=0", "type": "offer"})

    assert response.status_code == 422
    assert "slug or config" in response.json()["detail"]


async def test_calling_an_invalid_config_is_refused_before_answering(client, agent_config):
    agent_config["nodes"][2]["provider"] = "gpt"

    response = await client.post(
        "/calls", json={"sdp": "v=0", "type": "offer", "config": agent_config}
    )

    assert response.status_code == 422
    assert 'unknown llm provider "gpt"' in response.json()["detail"]["issues"][0]["message"]


async def test_no_calls_are_live_to_begin_with(client):
    assert (await client.get("/calls")).json() == []


async def test_events_for_an_unknown_call(client):
    assert (await client.get("/calls/nope/events")).status_code == 404


async def test_hanging_up_an_unknown_call(client):
    assert (await client.post("/calls/nope/hangup")).status_code == 404
