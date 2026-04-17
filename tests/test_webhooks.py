"""tests/test_webhooks.py — Unit tests for webhooks.py"""
import pytest
import respx
import httpx
import os

os.environ.setdefault("LITELLM_MASTER_KEY", "test-master-key")
os.environ.setdefault("WEBHOOK_URLS", "")

from fastapi.testclient import TestClient
from fastapi import FastAPI
import webhooks

app = FastAPI()
app.include_router(webhooks.router)
client = TestClient(app)

MASTER_KEY = "test-master-key"
AUTH = {"Authorization": f"Bearer {MASTER_KEY}"}


# ── POST /webhooks/register ──────────────────────────────────────────────

def test_register_webhook_no_auth():
    resp = client.post("/webhooks/register", json={
        "url": "https://example.com/hook", "events": ["agent.created"]
    })
    assert resp.status_code == 401


def test_register_webhook_success():
    webhooks._registered_webhooks.clear()
    resp = client.post("/webhooks/register", headers=AUTH, json={
        "url": "https://example.com/hook",
        "events": ["agent.created", "agent.suspended"],
        "secret": "s3cret",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "registered"
    assert len(webhooks._registered_webhooks) == 1


def test_register_webhook_wildcard():
    webhooks._registered_webhooks.clear()
    resp = client.post("/webhooks/register", headers=AUTH, json={
        "url": "https://example.com/all", "events": ["*"],
    })
    assert resp.status_code == 200


# ── GET /webhooks/ ───────────────────────────────────────────────────────

def test_list_webhooks_no_auth():
    resp = client.get("/webhooks/")
    assert resp.status_code == 401


def test_list_webhooks_empty():
    webhooks._registered_webhooks.clear()
    resp = client.get("/webhooks/", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_webhooks_returns_registered():
    webhooks._registered_webhooks.clear()
    webhooks._registered_webhooks.append(
        webhooks.WebhookConfig(url="https://a.com/hook", events=["agent.created"])
    )
    resp = client.get("/webhooks/", headers=AUTH)
    assert resp.status_code == 200
    hooks = resp.json()
    assert len(hooks) == 1
    assert hooks[0]["url"] == "https://a.com/hook"


# ── fire_webhook ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_fire_webhook_to_registered():
    webhooks._registered_webhooks.clear()
    webhooks._registered_webhooks.append(
        webhooks.WebhookConfig(url="https://a.com/hook", events=["agent.created"])
    )
    route = respx.post("https://a.com/hook").mock(return_value=httpx.Response(200))
    await webhooks.fire_webhook("agent.created", {"agent_id": "a1"})
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_fire_webhook_skips_unsubscribed():
    webhooks._registered_webhooks.clear()
    webhooks._registered_webhooks.append(
        webhooks.WebhookConfig(url="https://a.com/hook", events=["agent.suspended"])
    )
    route = respx.post("https://a.com/hook").mock(return_value=httpx.Response(200))
    await webhooks.fire_webhook("agent.created", {"agent_id": "a1"})
    assert not route.called


@pytest.mark.asyncio
@respx.mock
async def test_fire_webhook_wildcard_catches_all():
    webhooks._registered_webhooks.clear()
    webhooks._registered_webhooks.append(
        webhooks.WebhookConfig(url="https://a.com/all", events=["*"])
    )
    route = respx.post("https://a.com/all").mock(return_value=httpx.Response(200))
    await webhooks.fire_webhook("agent.revoked", {"agent_id": "a1"})
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_fire_webhook_failure_does_not_raise():
    webhooks._registered_webhooks.clear()
    webhooks._registered_webhooks.append(
        webhooks.WebhookConfig(url="https://down.com/hook", events=["*"])
    )
    respx.post("https://down.com/hook").mock(side_effect=httpx.ConnectError("down"))
    await webhooks.fire_webhook("agent.created", {"agent_id": "a1"})


@pytest.mark.asyncio
@respx.mock
async def test_fire_webhook_includes_secret_header():
    webhooks._registered_webhooks.clear()
    webhooks._registered_webhooks.append(
        webhooks.WebhookConfig(url="https://a.com/hook", events=["*"], secret="mysecret")
    )
    captured_headers = {}
    def capture(req, route):
        captured_headers.update(dict(req.headers))
        return httpx.Response(200)
    respx.post("https://a.com/hook").mock(side_effect=capture)
    await webhooks.fire_webhook("agent.created", {"agent_id": "a1"})
    assert captured_headers.get("x-webhook-secret") == "mysecret"
