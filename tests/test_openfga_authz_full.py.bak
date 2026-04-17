"""tests/test_openfga_authz_full.py
Coverage for openfga_authz.py — all auth paths.
Uses respx to mock OpenFGA HTTP calls.
"""
import pytest
import respx
import httpx
import os
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

os.environ.setdefault("OPENFGA_URL",           "http://openfga:8080")
os.environ.setdefault("OPENFGA_STORE_ID",      "test-store-id")
os.environ.setdefault("OPENFGA_AUTH_MODEL_ID", "test-model-id")
os.environ.setdefault("LITELLM_MASTER_KEY",    "test-master-key")

import openfga_authz as fga

app = FastAPI()
app.include_router(fga.router)
client = TestClient(app)

STORE_ID    = "test-store-id"
OPENFGA_URL = "http://openfga:8080"
MASTER_KEY  = "test-master-key"
AUTH        = {"Authorization": f"Bearer {MASTER_KEY}"}

CHECK_URL   = f"{OPENFGA_URL}/stores/{STORE_ID}/check"
WRITE_URL   = f"{OPENFGA_URL}/stores/{STORE_ID}/write"
LOBJS_URL   = f"{OPENFGA_URL}/stores/{STORE_ID}/list-objects"


# ── fga_check ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_fga_check_allowed():
    respx.post(CHECK_URL).mock(return_value=httpx.Response(200, json={"allowed": True}))
    assert await fga.fga_check("agent:x", "can_use_model", "model:y") is True

@pytest.mark.asyncio
@respx.mock
async def test_fga_check_denied():
    respx.post(CHECK_URL).mock(return_value=httpx.Response(200, json={"allowed": False}))
    assert await fga.fga_check("agent:x", "can_use_model", "model:y") is False

@pytest.mark.asyncio
async def test_fga_check_no_store_id_returns_true():
    """No STORE_ID → returns True (UNSAFE mode, logged as warning)."""
    import openfga_authz
    original = openfga_authz.OPENFGA_STORE_ID
    openfga_authz.OPENFGA_STORE_ID = ""
    try:
        result = await fga.fga_check("agent:x", "rel", "obj:y")
        assert result is True  # skips check entirely
    finally:
        openfga_authz.OPENFGA_STORE_ID = original

@pytest.mark.asyncio
@respx.mock
async def test_fga_check_http_error_returns_false():
    respx.post(CHECK_URL).mock(return_value=httpx.Response(500))
    assert await fga.fga_check("agent:x", "rel", "obj:y") is False

@pytest.mark.asyncio
@respx.mock
async def test_fga_check_network_error_returns_false():
    respx.post(CHECK_URL).mock(side_effect=httpx.ConnectError("down"))
    assert await fga.fga_check("agent:x", "rel", "obj:y") is False


# ── fga_write ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_fga_write_success():
    respx.post(WRITE_URL).mock(return_value=httpx.Response(200, json={}))
    result = await fga.fga_write([{
        "user": "agent:x", "relation": "can_use_model", "object": "model:y"
    }])
    assert result is True

@pytest.mark.asyncio
@respx.mock
async def test_fga_write_delete():
    """delete=True sends deletes key."""
    body = {}
    def capture(req, route):
        import json; nonlocal body; body = json.loads(req.content)
        return httpx.Response(200, json={})
    respx.post(WRITE_URL).mock(side_effect=capture)
    await fga.fga_write([{"user": "a", "relation": "r", "object": "o"}], delete=True)
    assert "deletes" in body

@pytest.mark.asyncio
@respx.mock
async def test_fga_write_failure():
    respx.post(WRITE_URL).mock(return_value=httpx.Response(400, json={"code": "bad"}))
    assert await fga.fga_write([{"user": "a", "relation": "r", "object": "o"}]) is False

@pytest.mark.asyncio
async def test_fga_write_no_store_id():
    import openfga_authz
    original = openfga_authz.OPENFGA_STORE_ID
    openfga_authz.OPENFGA_STORE_ID = ""
    try:
        result = await fga.fga_write([{"user": "a", "relation": "r", "object": "o"}])
        assert result is True  # skips, returns True (unsafe mode)
    finally:
        openfga_authz.OPENFGA_STORE_ID = original

@pytest.mark.asyncio
@respx.mock
async def test_fga_write_network_error():
    respx.post(WRITE_URL).mock(side_effect=httpx.ConnectError("down"))
    assert await fga.fga_write([{"user": "a", "relation": "r", "object": "o"}]) is False


# ── custom_auth ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_custom_auth_non_agent_passes():
    """Request with no agent_name in metadata passes without FGA check."""
    request = AsyncMock()
    request.metadata = {}
    request.model = "ollama/qwen3:30b-a3b"
    result = await fga.custom_auth(request)
    assert result is True

@pytest.mark.asyncio
@respx.mock
async def test_custom_auth_agent_allowed():
    respx.post(CHECK_URL).mock(return_value=httpx.Response(200, json={"allowed": True}))
    request = AsyncMock()
    request.metadata = {
        "agent_name": "fraud-sentinel",
        "tenant_id":  "tenant-acme",
    }
    request.model = "ollama/qwen3:30b-a3b"
    result = await fga.custom_auth(request)
    assert result is True

@pytest.mark.asyncio
@respx.mock
async def test_custom_auth_agent_denied():
    respx.post(CHECK_URL).mock(return_value=httpx.Response(200, json={"allowed": False}))
    request = AsyncMock()
    request.metadata = {"agent_name": "bad-agent", "tenant_id": "tenant-acme"}
    request.model = "gpt-4o"
    result = await fga.custom_auth(request)
    assert result is False

@pytest.mark.asyncio
async def test_custom_auth_exception_returns_false():
    """Exceptions during auth → fail closed (False)."""
    request = AsyncMock()
    request.metadata = {"agent_name": "x"}
    request.model = "ollama/qwen3:30b-a3b"
    # Make fga_check raise
    with patch.object(fga, "fga_check", side_effect=Exception("boom")):
        result = await fga.custom_auth(request)
    assert result is False


# ── POST /authz/grant ─────────────────────────────────────────────────────────

@respx.mock
def test_grant_success():
    respx.post(WRITE_URL).mock(return_value=httpx.Response(200, json={}))
    resp = client.post("/authz/grant", headers=AUTH, json={
        "user": "agent:fraud-sentinel",
        "relation": "can_use_model",
        "object": "model:qwen3-30b-a3b",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "granted"

@respx.mock
def test_grant_missing_auth():
    resp = client.post("/authz/grant", json={
        "user": "a", "relation": "r", "object": "o"
    })
    assert resp.status_code == 401

@respx.mock
def test_grant_fga_failure():
    respx.post(WRITE_URL).mock(return_value=httpx.Response(400, json={}))
    resp = client.post("/authz/grant", headers=AUTH, json={
        "user": "a", "relation": "r", "object": "o"
    })
    assert resp.status_code == 502


# ── POST /authz/revoke ────────────────────────────────────────────────────────

@respx.mock
def test_revoke_tuple_success():
    respx.post(WRITE_URL).mock(return_value=httpx.Response(200, json={}))
    resp = client.post("/authz/revoke", headers=AUTH, json={
        "user": "agent:fraud-sentinel",
        "relation": "can_use_model",
        "object": "model:gpt-4o",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "revoked"

@respx.mock
def test_revoke_tuple_missing_auth():
    resp = client.post("/authz/revoke", json={"user": "a", "relation": "r", "object": "o"})
    assert resp.status_code == 401


# ── POST /authz/check ─────────────────────────────────────────────────────────

@respx.mock
def test_check_allowed():
    respx.post(CHECK_URL).mock(return_value=httpx.Response(200, json={"allowed": True}))
    resp = client.post("/authz/check", headers=AUTH, json={
        "user": "agent:x", "relation": "can_use_model", "object": "model:y"
    })
    assert resp.status_code == 200
    assert resp.json()["allowed"] is True

@respx.mock
def test_check_denied():
    respx.post(CHECK_URL).mock(return_value=httpx.Response(200, json={"allowed": False}))
    resp = client.post("/authz/check", headers=AUTH, json={
        "user": "agent:x", "relation": "can_use_model", "object": "model:y"
    })
    assert resp.status_code == 200
    assert resp.json()["allowed"] is False

@respx.mock
def test_check_missing_auth():
    resp = client.post("/authz/check", json={"user": "a", "relation": "r", "object": "o"})
    assert resp.status_code == 401


# ── GET /authz/agent/{agent_name}/models ──────────────────────────────────────

@respx.mock
def test_list_agent_models_success():
    respx.post(LOBJS_URL).mock(return_value=httpx.Response(200, json={
        "objects": ["model:qwen3-30b-a3b", "model:groq-llama3-70b"]
    }))
    resp = client.get("/authz/agent/fraud-sentinel/models", headers=AUTH)
    assert resp.status_code == 200
    assert "qwen3-30b-a3b" in resp.json()["allowed_models"]

@respx.mock
def test_list_agent_models_empty():
    respx.post(LOBJS_URL).mock(return_value=httpx.Response(200, json={"objects": []}))
    resp = client.get("/authz/agent/unknown/models", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["allowed_models"] == []

@respx.mock
def test_list_agent_models_missing_auth():
    resp = client.get("/authz/agent/fraud-sentinel/models")
    assert resp.status_code == 401


# ── POST /authz/agent/{name}/grant-model/{model} ──────────────────────────────

@respx.mock
def test_grant_model_to_agent():
    respx.post(WRITE_URL).mock(return_value=httpx.Response(200, json={}))
    resp = client.post("/authz/agent/fraud-sentinel/grant-model/qwen3-30b-a3b", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "granted"

@respx.mock
def test_revoke_model_from_agent():
    respx.post(WRITE_URL).mock(return_value=httpx.Response(200, json={}))
    resp = client.post("/authz/agent/fraud-sentinel/revoke-model/gpt-4o", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "revoked"


# ── MODEL_ALIAS_MAP ───────────────────────────────────────────────────────────

def test_model_alias_map_not_empty():
    assert len(fga.MODEL_ALIAS_MAP) > 0

def test_model_alias_map_values_prefixed():
    for alias, name in fga.MODEL_ALIAS_MAP.items():
        assert name.startswith("model:"), f"Bad mapping: {alias} → {name}"

def test_ollama_models_in_alias_map():
    for m in ["ollama/qwen3:30b-a3b", "ollama/qwen2.5-coder:32b"]:
        assert m in fga.MODEL_ALIAS_MAP, f"{m} not in MODEL_ALIAS_MAP"
