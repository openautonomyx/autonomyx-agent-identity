import os

from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LITELLM_MASTER_KEY", "test-master-key")

from main import app

client = TestClient(app)


def test_live_health_endpoint():
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_request_id_headers_present():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "X-Request-Id" in resp.headers
    assert "X-Process-Time-Ms" in resp.headers


def test_secure_headers_present():
    resp = client.get("/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
