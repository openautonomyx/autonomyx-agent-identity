"""tests/test_audit.py — Unit tests for audit.py"""
import pytest
import respx
import httpx
import os

os.environ.setdefault("LITELLM_MASTER_KEY", "test-master-key")
os.environ.setdefault("SURREAL_URL", "http://surrealdb:8000")
os.environ.setdefault("SURREAL_NS", "autonomyx")
os.environ.setdefault("SURREAL_DB", "agents")
os.environ.setdefault("SURREAL_USER", "root")
os.environ.setdefault("SURREAL_PASS", "root")

from fastapi.testclient import TestClient
from fastapi import FastAPI
import audit

app = FastAPI()
app.include_router(audit.router)
client = TestClient(app)

SURREAL_URL = "http://surrealdb:8000"
MASTER_KEY = "test-master-key"
AUTH = {"Authorization": f"Bearer {MASTER_KEY}"}

SAMPLE_AUDIT_EVENT = {
    "id": "audit:2026-01-01T00-00-00_agent001",
    "event_type": "agent.created",
    "agent_id": "agent-001",
    "agent_name": "fraud-sentinel",
    "actor_id": "sponsor@test.com",
    "actor_type": "human",
    "tenant_id": "tenant-acme",
    "timestamp": "2026-01-01T00:00:00+00:00",
    "details": {},
    "ip_address": "127.0.0.1",
}


def surreal_events(events=None):
    return httpx.Response(200, json=[{"result": events or [SAMPLE_AUDIT_EVENT], "status": "OK"}])


def surreal_empty():
    return httpx.Response(200, json=[{"result": [], "status": "OK"}])


# ── log_event ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_log_event_writes_to_surreal():
    route = respx.post(f"{SURREAL_URL}/sql").mock(
        return_value=httpx.Response(200, json=[{"result": [], "status": "OK"}])
    )
    await audit.log_event(
        event_type="agent.created",
        agent_id="agent-001",
        agent_name="fraud-sentinel",
        actor_id="sponsor@test.com",
        tenant_id="tenant-acme",
    )
    assert route.called


@pytest.mark.asyncio
async def test_log_event_no_surreal_url():
    original = audit.SURREAL_URL
    audit.SURREAL_URL = ""
    try:
        await audit.log_event("agent.created", "a1", "test", "actor")
    finally:
        audit.SURREAL_URL = original


@pytest.mark.asyncio
@respx.mock
async def test_log_event_failure_does_not_raise():
    respx.post(f"{SURREAL_URL}/sql").mock(return_value=httpx.Response(500))
    await audit.log_event("agent.created", "a1", "test", "actor")


# ── VictoriaLogs push ─────────────────────────────────────────────────────

VLOGS_URL = "http://victorialogs:9428"


@pytest.mark.asyncio
@respx.mock
async def test_push_to_victorialogs_success():
    original = audit.VICTORIALOGS_URL
    audit.VICTORIALOGS_URL = VLOGS_URL
    try:
        route = respx.post(f"{VLOGS_URL}/insert/jsonline").mock(
            return_value=httpx.Response(200)
        )
        await audit._push_to_victorialogs({
            "event_type": "agent.created", "agent_id": "a1",
            "agent_name": "test", "actor_id": "actor",
            "actor_type": "human", "tenant_id": "t1",
            "timestamp": "2026-01-01T00:00:00+00:00",
        })
        assert route.called
    finally:
        audit.VICTORIALOGS_URL = original


@pytest.mark.asyncio
async def test_push_to_victorialogs_skips_when_no_url():
    original = audit.VICTORIALOGS_URL
    audit.VICTORIALOGS_URL = ""
    try:
        await audit._push_to_victorialogs({"event_type": "test"})
    finally:
        audit.VICTORIALOGS_URL = original


@pytest.mark.asyncio
@respx.mock
async def test_push_to_victorialogs_failure_does_not_raise():
    original = audit.VICTORIALOGS_URL
    audit.VICTORIALOGS_URL = VLOGS_URL
    try:
        respx.post(f"{VLOGS_URL}/insert/jsonline").mock(
            side_effect=httpx.ConnectError("down")
        )
        await audit._push_to_victorialogs({
            "event_type": "agent.created", "agent_id": "a1",
            "agent_name": "test", "actor_id": "actor",
            "actor_type": "human", "tenant_id": "t1",
            "timestamp": "2026-01-01T00:00:00+00:00",
        })
    finally:
        audit.VICTORIALOGS_URL = original


@pytest.mark.asyncio
@respx.mock
async def test_log_event_dual_writes():
    original = audit.VICTORIALOGS_URL
    audit.VICTORIALOGS_URL = VLOGS_URL
    try:
        surreal_route = respx.post(f"{SURREAL_URL}/sql").mock(
            return_value=httpx.Response(200, json=[{"result": [], "status": "OK"}])
        )
        vlogs_route = respx.post(f"{VLOGS_URL}/insert/jsonline").mock(
            return_value=httpx.Response(200)
        )
        await audit.log_event("agent.created", "a1", "test-agent", "actor")
        assert surreal_route.called
        assert vlogs_route.called
    finally:
        audit.VICTORIALOGS_URL = original


# ── GET /audit/ ────────────────────────────────────────────────────────────

@respx.mock
def test_list_audit_events_no_auth():
    resp = client.get("/audit/")
    assert resp.status_code == 401


@respx.mock
def test_list_audit_events_empty():
    respx.post(f"{SURREAL_URL}/sql").mock(return_value=surreal_empty())
    resp = client.get("/audit/", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == []


@respx.mock
def test_list_audit_events_returns_events():
    respx.post(f"{SURREAL_URL}/sql").mock(return_value=surreal_events())
    resp = client.get("/audit/", headers=AUTH)
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) == 1
    assert events[0]["event_type"] == "agent.created"


@respx.mock
def test_list_audit_events_filter_by_agent():
    respx.post(f"{SURREAL_URL}/sql").mock(return_value=surreal_events())
    resp = client.get("/audit/?agent_id=agent-001", headers=AUTH)
    assert resp.status_code == 200


@respx.mock
def test_list_audit_events_filter_by_event_type():
    respx.post(f"{SURREAL_URL}/sql").mock(return_value=surreal_events())
    resp = client.get("/audit/?event_type=agent.created", headers=AUTH)
    assert resp.status_code == 200


# ── GET /audit/agent/{agent_id} ───────────────────────────────────────────

@respx.mock
def test_get_agent_audit_trail_no_auth():
    resp = client.get("/audit/agent/agent-001")
    assert resp.status_code == 401


@respx.mock
def test_get_agent_audit_trail_success():
    respx.post(f"{SURREAL_URL}/sql").mock(return_value=surreal_events())
    resp = client.get("/audit/agent/agent-001", headers=AUTH)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@respx.mock
def test_get_agent_audit_trail_empty():
    respx.post(f"{SURREAL_URL}/sql").mock(return_value=surreal_empty())
    resp = client.get("/audit/agent/nonexistent", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == []


# ── GET /audit/sponsor/{sponsor_id} ──────────────────────────────────────

@respx.mock
def test_get_sponsor_audit_trail():
    respx.post(f"{SURREAL_URL}/sql").mock(return_value=surreal_events())
    resp = client.get("/audit/sponsor/sponsor@test.com", headers=AUTH)
    assert resp.status_code == 200


# ── GET /audit/tenant/{tenant_id} ────────────────────────────────────────

@respx.mock
def test_get_tenant_audit_trail():
    respx.post(f"{SURREAL_URL}/sql").mock(return_value=surreal_events())
    resp = client.get("/audit/tenant/tenant-acme", headers=AUTH)
    assert resp.status_code == 200
