"""tests/test_bulk_ops.py — Unit tests for bulk_ops.py"""
import pytest
import respx
import httpx
import os
from unittest.mock import AsyncMock, patch

os.environ.setdefault("LITELLM_MASTER_KEY", "test-master-key")
os.environ.setdefault("LITELLM_URL", "http://litellm:4000")
os.environ.setdefault("SURREAL_URL", "http://surrealdb:8000")
os.environ.setdefault("SURREAL_NS", "autonomyx")
os.environ.setdefault("SURREAL_DB", "agents")
os.environ.setdefault("SURREAL_USER", "root")
os.environ.setdefault("SURREAL_PASS", "root")

from fastapi.testclient import TestClient
from fastapi import FastAPI
import bulk_ops

app = FastAPI()
app.include_router(bulk_ops.router)
client = TestClient(app)

MASTER_KEY = "test-master-key"
AUTH = {"Authorization": f"Bearer {MASTER_KEY}"}


# ── POST /bulk/suspend ───────────────────────────────────────────────────

def test_bulk_suspend_no_auth():
    resp = client.post("/bulk/suspend", json={"agent_ids": ["a1"]})
    assert resp.status_code == 401


@patch("agent_identity.suspend_agent", new_callable=AsyncMock)
def test_bulk_suspend_success(mock_suspend):
    mock_suspend.return_value = {"status": "suspended"}
    resp = client.post("/bulk/suspend", headers=AUTH, json={
        "agent_ids": ["agent-001", "agent-002"]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["succeeded"]) == 2
    assert len(data["failed"]) == 0


@patch("agent_identity.suspend_agent", new_callable=AsyncMock)
def test_bulk_suspend_partial_failure(mock_suspend):
    async def side_effect(aid, auth):
        if aid == "agent-bad":
            raise Exception("Not found")
        return {"status": "suspended"}
    mock_suspend.side_effect = side_effect
    resp = client.post("/bulk/suspend", headers=AUTH, json={
        "agent_ids": ["agent-001", "agent-bad"]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["succeeded"]) == 1
    assert len(data["failed"]) == 1
    assert data["failed"][0]["agent_id"] == "agent-bad"


def test_bulk_suspend_empty_list():
    resp = client.post("/bulk/suspend", headers=AUTH, json={"agent_ids": []})
    assert resp.status_code == 200
    assert resp.json()["succeeded"] == []


# ── POST /bulk/revoke ────────────────────────────────────────────────────

def test_bulk_revoke_no_auth():
    resp = client.post("/bulk/revoke", json={"agent_ids": ["a1"]})
    assert resp.status_code == 401


@patch("agent_identity.revoke_agent", new_callable=AsyncMock)
def test_bulk_revoke_success(mock_revoke):
    mock_revoke.return_value = {"status": "revoked"}
    resp = client.post("/bulk/revoke", headers=AUTH, json={
        "agent_ids": ["agent-001", "agent-002"]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["succeeded"]) == 2


@patch("agent_identity.revoke_agent", new_callable=AsyncMock)
def test_bulk_revoke_all_fail(mock_revoke):
    mock_revoke.side_effect = Exception("DB down")
    resp = client.post("/bulk/revoke", headers=AUTH, json={
        "agent_ids": ["a1", "a2"]
    })
    assert resp.status_code == 200
    assert len(resp.json()["failed"]) == 2
