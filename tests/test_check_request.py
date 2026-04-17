"""tests/test_check_request.py — Tests for APISIX forward-auth endpoint"""
import pytest
import respx
import httpx
import os
from unittest.mock import AsyncMock, patch

os.environ.setdefault("LITELLM_MASTER_KEY", "test-master-key")
os.environ.setdefault("SURREAL_URL", "http://surrealdb:8000")
os.environ.setdefault("SURREAL_NS", "autonomyx")
os.environ.setdefault("SURREAL_DB", "agents")
os.environ.setdefault("SURREAL_USER", "root")
os.environ.setdefault("SURREAL_PASS", "root")
os.environ.setdefault("OPENFGA_STORE_ID", "test-store")

from fastapi.testclient import TestClient
from fastapi import FastAPI
import openfga_authz

app = FastAPI()
app.include_router(openfga_authz.router)
client = TestClient(app)

MASTER_KEY = "test-master-key"


def test_check_request_no_auth():
    resp = client.get("/authz/check-request")
    assert resp.status_code == 401


def test_check_request_master_key():
    resp = client.get("/authz/check-request",
                      headers={"Authorization": f"Bearer {MASTER_KEY}"})
    assert resp.status_code == 200
    assert resp.headers.get("x-agent-id") == "admin"


@patch("openfga_authz.fga_check", new_callable=AsyncMock)
@patch("agent_identity._surreal_query", new_callable=AsyncMock)
def test_check_request_valid_agent(mock_surreal, mock_fga):
    mock_surreal.return_value = [{"result": [{
        "agent_id": "a1", "agent_name": "test-agent",
        "tenant_id": "t1", "status": "active",
        "litellm_key_alias": "sk-agent-key",
    }], "status": "OK"}]
    mock_fga.return_value = True
    resp = client.get("/authz/check-request",
                      headers={
                          "Authorization": "Bearer sk-agent-key",
                          "X-Forwarded-Uri": "/identity/agents",
                      })
    assert resp.status_code == 200
    assert resp.headers.get("x-agent-name") == "test-agent"
    assert resp.headers.get("x-tenant-id") == "t1"


@patch("agent_identity._surreal_query", new_callable=AsyncMock)
def test_check_request_invalid_key(mock_surreal):
    mock_surreal.return_value = [{"result": [], "status": "OK"}]
    resp = client.get("/authz/check-request",
                      headers={"Authorization": "Bearer bad-key"})
    assert resp.status_code == 401


@patch("openfga_authz.fga_check", new_callable=AsyncMock)
@patch("agent_identity._surreal_query", new_callable=AsyncMock)
def test_check_request_suspended_agent(mock_surreal, mock_fga):
    mock_surreal.return_value = [{"result": [{
        "agent_id": "a1", "agent_name": "test-agent",
        "tenant_id": "t1", "status": "suspended",
    }], "status": "OK"}]
    resp = client.get("/authz/check-request",
                      headers={"Authorization": "Bearer sk-suspended"})
    assert resp.status_code == 403


@patch("openfga_authz.fga_check", new_callable=AsyncMock)
@patch("agent_identity._surreal_query", new_callable=AsyncMock)
def test_check_request_fga_denied(mock_surreal, mock_fga):
    mock_surreal.return_value = [{"result": [{
        "agent_id": "a1", "agent_name": "test-agent",
        "tenant_id": "t1", "status": "active",
    }], "status": "OK"}]
    mock_fga.return_value = False
    resp = client.get("/authz/check-request",
                      headers={
                          "Authorization": "Bearer sk-no-access",
                          "X-Forwarded-Uri": "/grafana/dashboards",
                      })
    assert resp.status_code == 403
