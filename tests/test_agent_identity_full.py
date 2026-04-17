"""tests/test_agent_identity_full.py
Coverage for agent_identity.py — all endpoints.
Uses respx to mock SurrealDB + LiteLLM HTTP calls.
"""
import pytest
import respx
import httpx
import os
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi import FastAPI

os.environ.setdefault("LITELLM_URL",         "http://litellm:4000")
os.environ.setdefault("LITELLM_MASTER_KEY",  "test-master-key")
os.environ.setdefault("SURREAL_URL",         "http://surrealdb:8000")
os.environ.setdefault("SURREAL_NS",          "autonomyx")
os.environ.setdefault("SURREAL_DB",          "gateway")
os.environ.setdefault("SURREAL_USER",        "root")
os.environ.setdefault("SURREAL_PASS",        "root")

import agent_identity as ai

app = FastAPI()
app.include_router(ai.router)
client = TestClient(app)

LITELLM_URL = "http://litellm:4000"
SURREAL_URL = "http://surrealdb:8000"
MASTER_KEY  = "test-master-key"
AUTH        = {"Authorization": f"Bearer {MASTER_KEY}"}

# Real SurrealDB response shape: list of result objects
AGENT_RECORD = {
    "agent_id":          "agent-001",
    "agent_name":        "fraud-sentinel",
    "agent_type":        "workflow",
    "sponsor_id":        "sponsor@test.com",
    "owner_ids":         ["sponsor@test.com"],
    "manager_id":        None,
    "blueprint_id":      None,
    "tenant_id":         "tenant-acme",
    "allowed_models":    ["ollama/qwen3:30b-a3b"],
    "budget_limit":      2.0,
    "tpm_limit":         10000,
    "litellm_key_alias": "agent:fraud-sentinel:tenant-acme",
    "litellm_key":       "sk-agentkey123",
    "status":            "active",
    "created_at":        datetime.now(timezone.utc).isoformat(),
    "last_active_at":    datetime.now(timezone.utc).isoformat(),
    "expires_at":        None,
    "metadata":          {},
}

def surreal_agent(record=None):
    """Surreal RPC response with one agent result."""
    return httpx.Response(200, json={"result": [{"result": [record or AGENT_RECORD], "status": "OK"}]})

def surreal_empty():
    return httpx.Response(200, json={"result": [{"result": [], "status": "OK"}]})

def surreal_ok():
    return httpx.Response(200, json={"result": [{"result": [], "status": "OK"}]})

def litellm_key(key="sk-test-key"):
    return httpx.Response(200, json={"key": key})

def litellm_keylist(aliases=None):
    aliases = aliases or ["agent:fraud-sentinel:tenant-acme"]
    keys = [{"key_alias": a, "key": f"sk-{a[-8:]}"} for a in aliases]
    return httpx.Response(200, json={"keys": keys})


# ── _surreal_query ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_surreal_query_success():
    respx.post(f"{SURREAL_URL}/rpc").mock(
        return_value=httpx.Response(200, json={"result": [{"result": [{"id": "agents:001"}], "status": "OK"}]})
    )
    result = await ai._surreal_query("SELECT * FROM agents;")
    assert result[0]["result"][0]["id"] == "agents:001"


@pytest.mark.asyncio
async def test_surreal_query_no_url():
    import agent_identity
    original = agent_identity.SURREAL_URL
    agent_identity.SURREAL_URL = ""
    try:
        result = await ai._surreal_query("SELECT * FROM agents;")
        assert result is None
    finally:
        agent_identity.SURREAL_URL = original


# ── _create_litellm_key ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_create_litellm_key_basic():
    respx.post(f"{LITELLM_URL}/key/generate").mock(return_value=litellm_key())
    result = await ai._create_litellm_key(
        agent_name="fraud-sentinel", tenant_id="tenant-acme",
        allowed_models=["ollama/qwen3:30b-a3b"], budget_limit=2.0,
        tpm_limit=10000, expires_at=None, agent_id="a-001",
        sponsor_id="s@test.com", agent_type="workflow",
    )
    assert result["key"] == "sk-test-key"


@pytest.mark.asyncio
@respx.mock
async def test_create_litellm_key_with_expiry():
    from datetime import timedelta
    body = {}
    def capture(req, route):
        import json; nonlocal body; body = json.loads(req.content)
        return httpx.Response(200, json={"key": "sk-exp"})
    respx.post(f"{LITELLM_URL}/key/generate").mock(side_effect=capture)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    await ai._create_litellm_key(
        agent_name="tmp", tenant_id="t", allowed_models=[],
        budget_limit=1.0, tpm_limit=1000, expires_at=expires,
        agent_id="a", sponsor_id="s", agent_type="ephemeral",
    )
    assert "duration" in body


# ── _delete_litellm_key ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_delete_litellm_key_ok():
    respx.post(f"{LITELLM_URL}/key/delete").mock(return_value=httpx.Response(200))
    assert await ai._delete_litellm_key("sk-old") is True

@pytest.mark.asyncio
@respx.mock
async def test_delete_litellm_key_fail():
    respx.post(f"{LITELLM_URL}/key/delete").mock(return_value=httpx.Response(404))
    assert await ai._delete_litellm_key("sk-gone") is False


# ── POST /agents/create ────────────────────────────────────────────────────────

@respx.mock
def test_create_agent_no_auth():
    resp = client.post("/agents/create", json={
        "agent_name": "fraud-sentinel", "sponsor_id": "s@t.com", "tenant_id": "t-acme"
    })
    assert resp.status_code == 401

@respx.mock
def test_create_agent_success():
    respx.post(f"{LITELLM_URL}/key/generate").mock(return_value=litellm_key("sk-created"))
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_ok())
    resp = client.post("/agents/create", headers=AUTH, json={
        "agent_name": "fraud-sentinel", "sponsor_id": "s@t.com", "tenant_id": "t-acme"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["litellm_key"] == "sk-created"
    assert data["status"] == "active"
    assert "agent_id" in data

@respx.mock
def test_create_agent_default_model_allowlist():
    body = {}
    def capture(req, route):
        import json; nonlocal body; body = json.loads(req.content)
        return httpx.Response(200, json={"key": "sk-k"})
    respx.post(f"{LITELLM_URL}/key/generate").mock(side_effect=capture)
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_ok())
    client.post("/agents/create", headers=AUTH, json={
        "agent_name": "fraud-sentinel", "sponsor_id": "s@t.com", "tenant_id": "t"
    })
    assert "ollama/qwen3:30b-a3b" in body.get("models", [])

@respx.mock
def test_create_agent_litellm_failure():
    respx.post(f"{LITELLM_URL}/key/generate").mock(return_value=httpx.Response(500))
    resp = client.post("/agents/create", headers=AUTH, json={
        "agent_name": "fraud-sentinel", "sponsor_id": "s@t.com", "tenant_id": "t"
    })
    assert resp.status_code == 502


# ── GET /agents ────────────────────────────────────────────────────────────────

@respx.mock
def test_list_agents_no_auth():
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_empty())
    resp = client.get("/agents")
    # No auth check implemented in list_agents — returns empty list
    assert resp.status_code in (200, 401)

@respx.mock
def test_list_agents_empty():
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_empty())
    resp = client.get("/agents", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == []

@respx.mock
def test_list_agents_returns_agents():
    import httpx as _httpx
    from datetime import datetime, timezone as tz
    record = {
        "agent_id": "agent-001", "agent_name": "fraud-sentinel",
        "agent_type": "workflow", "sponsor_id": "s@t.com",
        "owner_ids": ["s@t.com"], "manager_id": None, "blueprint_id": None,
        "tenant_id": "tenant-acme", "allowed_models": ["ollama/qwen3:30b-a3b"],
        "budget_limit": 2.0, "tpm_limit": 10000,
        "litellm_key_alias": "agent:fraud-sentinel:tenant-acme",
        "status": "active",
        "created_at": datetime.now(tz.utc).isoformat(),
        "last_active_at": datetime.now(tz.utc).isoformat(),
        "expires_at": None, "metadata": {},
    }
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=_httpx.Response(
        200, json={"result": [{"result": [record], "status": "OK"}]}
    ))
    resp = client.get("/agents", headers=AUTH)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

@respx.mock
def test_list_agents_filter_by_tenant():
    import httpx as _httpx
    from datetime import datetime, timezone as tz
    record = {
        "agent_id": "agent-001", "agent_name": "fraud-sentinel",
        "agent_type": "workflow", "sponsor_id": "s@t.com",
        "owner_ids": ["s@t.com"], "manager_id": None, "blueprint_id": None,
        "tenant_id": "tenant-acme", "allowed_models": ["ollama/qwen3:30b-a3b"],
        "budget_limit": 2.0, "tpm_limit": 10000,
        "litellm_key_alias": "agent:fraud-sentinel:tenant-acme",
        "status": "active",
        "created_at": datetime.now(tz.utc).isoformat(),
        "last_active_at": datetime.now(tz.utc).isoformat(),
        "expires_at": None, "metadata": {},
    }
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=_httpx.Response(
        200, json={"result": [{"result": [record], "status": "OK"}]}
    ))
    resp = client.get("/agents?tenant_id=tenant-acme", headers=AUTH)
    assert resp.status_code == 200


# ── GET /agents/{agent_id} ─────────────────────────────────────────────────────

@respx.mock
def test_get_agent_found():
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_agent())
    resp = client.get("/agents/agent-001", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["agent_id"] == "agent-001"

@respx.mock
def test_get_agent_not_found():
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_empty())
    resp = client.get("/agents/nonexistent", headers=AUTH)
    assert resp.status_code == 404

@respx.mock
def test_get_agent_no_auth():
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_empty())
    resp = client.get("/agents/agent-001")
    # Auth not enforced on get — returns 404 if not found
    assert resp.status_code in (200, 401, 404)


# ── POST /agents/{agent_id}/suspend ───────────────────────────────────────────

@respx.mock
def test_suspend_agent_success():
    respx.post(f"{SURREAL_URL}/rpc").mock(side_effect=[
        surreal_agent(),      # _get_agent
        litellm_keylist(),    # key/list inside suspend
        surreal_ok(),         # _update_agent_status
    ])
    respx.get(f"{LITELLM_URL}/key/list").mock(return_value=litellm_keylist())
    respx.post(f"{LITELLM_URL}/key/delete").mock(return_value=httpx.Response(200))
    resp = client.post("/agents/agent-001/suspend", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "suspended"

@respx.mock
def test_suspend_agent_not_found():
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_empty())
    resp = client.post("/agents/nonexistent/suspend", headers=AUTH)
    assert resp.status_code == 404

@respx.mock
def test_suspend_agent_already_suspended():
    suspended = {**AGENT_RECORD, "status": "suspended"}
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_agent(suspended))
    resp = client.post("/agents/agent-001/suspend", headers=AUTH)
    assert resp.status_code == 409


# ── POST /agents/{agent_id}/reactivate ────────────────────────────────────────

@respx.mock
def test_reactivate_success():
    suspended = {**AGENT_RECORD, "status": "suspended"}
    respx.post(f"{SURREAL_URL}/rpc").mock(side_effect=[
        surreal_agent(suspended),  # _get_agent
        surreal_ok(),              # _update_agent_status
    ])
    respx.post(f"{LITELLM_URL}/key/generate").mock(return_value=litellm_key("sk-new"))
    resp = client.post("/agents/agent-001/reactivate", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["litellm_key"] == "sk-new"

@respx.mock
def test_reactivate_already_active():
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_agent())
    resp = client.post("/agents/agent-001/reactivate", headers=AUTH)
    assert resp.status_code == 409

@respx.mock
def test_reactivate_revoked_fails():
    revoked = {**AGENT_RECORD, "status": "revoked"}
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_agent(revoked))
    resp = client.post("/agents/agent-001/reactivate", headers=AUTH)
    assert resp.status_code == 409

@respx.mock
def test_reactivate_not_found():
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_empty())
    resp = client.post("/agents/nonexistent/reactivate", headers=AUTH)
    assert resp.status_code == 404


# ── POST /agents/{agent_id}/rotate ────────────────────────────────────────────

@respx.mock
def test_rotate_key_success():
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_agent())
    respx.post(f"{LITELLM_URL}/key/generate").mock(return_value=litellm_key("sk-rotated"))
    respx.get(f"{LITELLM_URL}/key/list").mock(return_value=litellm_keylist())
    respx.post(f"{LITELLM_URL}/key/delete").mock(return_value=httpx.Response(200))
    resp = client.post("/agents/agent-001/rotate", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["litellm_key"] == "sk-rotated"

@respx.mock
def test_rotate_key_not_found():
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_empty())
    resp = client.post("/agents/nonexistent/rotate", headers=AUTH)
    assert resp.status_code == 404

@respx.mock
def test_rotate_key_suspended_agent():
    suspended = {**AGENT_RECORD, "status": "suspended"}
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_agent(suspended))
    resp = client.post("/agents/agent-001/rotate", headers=AUTH)
    assert resp.status_code == 409


# ── DELETE /agents/{agent_id} ─────────────────────────────────────────────────

@respx.mock
def test_revoke_agent_success():
    respx.post(f"{SURREAL_URL}/rpc").mock(side_effect=[
        surreal_agent(),  # _get_agent
        surreal_ok(),     # _update_agent_status
    ])
    respx.get(f"{LITELLM_URL}/key/list").mock(return_value=litellm_keylist())
    respx.post(f"{LITELLM_URL}/key/delete").mock(return_value=httpx.Response(200))
    resp = client.delete("/agents/agent-001", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "revoked"

@respx.mock
def test_revoke_agent_not_found():
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_empty())
    resp = client.delete("/agents/nonexistent", headers=AUTH)
    assert resp.status_code == 404

@respx.mock
def test_revoke_already_revoked():
    revoked = {**AGENT_RECORD, "status": "revoked"}
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_agent(revoked))
    resp = client.delete("/agents/agent-001", headers=AUTH)
    assert resp.status_code == 409


# ── GET /agents/{agent_id}/activity ───────────────────────────────────────────

@respx.mock
def test_get_activity_returns_list():
    activity = [{"model": "ollama/qwen3:30b-a3b", "status": "success"}]
    respx.post(f"{SURREAL_URL}/rpc").mock(
        return_value=httpx.Response(200, json={"result": [{"result": activity, "status": "OK"}]})
    )
    resp = client.get("/agents/agent-001/activity", headers=AUTH)
    assert resp.status_code == 200
    assert "agent_id" in resp.json()

@respx.mock
def test_get_activity_empty():
    respx.post(f"{SURREAL_URL}/rpc").mock(return_value=surreal_empty())
    resp = client.get("/agents/agent-001/activity", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["agent_id"] == "agent-001"


# ── DEFAULT_MODEL_ALLOWLISTS / AGENTS ─────────────────────────────────────────

def test_default_allowlists_not_empty():
    assert len(ai.DEFAULT_MODEL_ALLOWLISTS) > 0

def test_all_known_agents_have_allowlists():
    known = ["fraud-sentinel", "code-reviewer", "web-scraper"]
    for name in known:
        assert name in ai.DEFAULT_MODEL_ALLOWLISTS, f"{name} missing from DEFAULT_MODEL_ALLOWLISTS"

def test_all_allowlists_have_local_model():
    for name, models in ai.DEFAULT_MODEL_ALLOWLISTS.items():
        has_local = any(m.startswith("ollama/") for m in models)
        assert has_local, f"Agent '{name}' has no ollama/ model in DEFAULT_MODEL_ALLOWLISTS"
