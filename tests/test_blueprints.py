"""tests/test_blueprints.py — Unit tests for blueprints.py"""
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
import blueprints

app = FastAPI()
app.include_router(blueprints.router)
client = TestClient(app)

SURREAL_URL = "http://surrealdb:8000"
MASTER_KEY = "test-master-key"
AUTH = {"Authorization": f"Bearer {MASTER_KEY}"}

SAMPLE_BLUEPRINT = {
    "blueprint_id": "bp-001",
    "name": "fraud-detector-template",
    "description": "Template for fraud detection agents",
    "agent_type": "workflow",
    "default_models": ["ollama/qwen3:30b-a3b"],
    "default_budget": 5.0,
    "default_tpm": 10000,
    "owner_id": "admin@test.com",
    "created_at": "2026-01-01T00:00:00+00:00",
    "agents_created": 0,
}


def surreal_blueprint(bp=None):
    return httpx.Response(200, json=[{"result": [bp or SAMPLE_BLUEPRINT], "status": "OK"}])


def surreal_empty():
    return httpx.Response(200, json=[{"result": [], "status": "OK"}])


def surreal_ok():
    return httpx.Response(200, json=[{"result": [], "status": "OK"}])


# ── POST /blueprints/create ──────────────────────────────────────────────

@respx.mock
def test_create_blueprint_no_auth():
    resp = client.post("/blueprints/create", json={"name": "test"})
    assert resp.status_code == 401


@respx.mock
def test_create_blueprint_success():
    respx.post(f"{SURREAL_URL}/sql").mock(return_value=surreal_ok())
    resp = client.post("/blueprints/create", headers=AUTH, json={
        "name": "fraud-detector-template",
        "description": "Template for fraud agents",
        "agent_type": "workflow",
        "default_models": ["ollama/qwen3:30b-a3b"],
        "default_budget": 5.0,
        "owner_id": "admin@test.com",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "fraud-detector-template"
    assert "blueprint_id" in data
    assert data["agents_created"] == 0


@respx.mock
def test_create_blueprint_defaults():
    respx.post(f"{SURREAL_URL}/sql").mock(return_value=surreal_ok())
    resp = client.post("/blueprints/create", headers=AUTH, json={"name": "minimal"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_type"] == "workflow"
    assert data["default_budget"] == 5.0


# ── GET /blueprints/ ─────────────────────────────────────────────────────

@respx.mock
def test_list_blueprints_no_auth():
    resp = client.get("/blueprints/")
    assert resp.status_code == 401


@respx.mock
def test_list_blueprints_empty():
    respx.post(f"{SURREAL_URL}/sql").mock(return_value=surreal_empty())
    resp = client.get("/blueprints/", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == []


@respx.mock
def test_list_blueprints_returns_data():
    respx.post(f"{SURREAL_URL}/sql").mock(return_value=surreal_blueprint())
    resp = client.get("/blueprints/", headers=AUTH)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "fraud-detector-template"


# ── GET /blueprints/{blueprint_id} ───────────────────────────────────────

@respx.mock
def test_get_blueprint_not_found():
    respx.post(f"{SURREAL_URL}/sql").mock(return_value=surreal_empty())
    resp = client.get("/blueprints/nonexistent", headers=AUTH)
    assert resp.status_code == 404


@respx.mock
def test_get_blueprint_success():
    respx.post(f"{SURREAL_URL}/sql").mock(return_value=surreal_blueprint())
    resp = client.get("/blueprints/bp-001", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["blueprint_id"] == "bp-001"
