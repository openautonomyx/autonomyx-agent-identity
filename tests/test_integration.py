"""tests/test_integration.py — Integration tests using Testcontainers.

Spins up real SurrealDB + OpenFGA containers per session.
LiteLLM functions are patched (external service on Server 1).
Run with: pytest -m integration
"""
import pytest
import httpx
import os
import uuid
import time
from unittest.mock import AsyncMock, patch
from testcontainers.core.container import DockerContainer

pytestmark = pytest.mark.integration

MASTER_KEY = "test-master-key"
SURREAL_USER = "root"
SURREAL_PASS = "testpass"


def _wait_for_http(url, path="/health", retries=20, delay=1):
    for _ in range(retries):
        try:
            r = httpx.get(f"{url}{path}", timeout=2)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(delay)
    raise RuntimeError(f"{url}{path} did not become healthy in {retries * delay}s")


@pytest.fixture(scope="session")
def surrealdb_container():
    container = (
        DockerContainer("surrealdb/surrealdb:v2.3.6")
        .with_exposed_ports(8000)
        .with_command(
            f"start --log=info --user={SURREAL_USER} --pass={SURREAL_PASS} memory"
        )
    )
    container.start()
    host = container.get_container_host_ip()
    port = container.get_exposed_port(8000)
    _wait_for_http(f"http://{host}:{port}", "/health")
    yield container
    container.stop()


@pytest.fixture(scope="session")
def openfga_container():
    container = (
        DockerContainer("openfga/openfga:v1.8.0")
        .with_exposed_ports(8080)
        .with_command("run")
        .with_env("OPENFGA_DATASTORE_ENGINE", "memory")
    )
    container.start()
    host = container.get_container_host_ip()
    port = container.get_exposed_port(8080)
    _wait_for_http(f"http://{host}:{port}", "/healthz")
    yield container
    container.stop()


@pytest.fixture(scope="session")
def setup_env(surrealdb_container, openfga_container):
    surreal_host = surrealdb_container.get_container_host_ip()
    surreal_port = surrealdb_container.get_exposed_port(8000)
    surreal_url = f"http://{surreal_host}:{surreal_port}"

    fga_host = openfga_container.get_container_host_ip()
    fga_port = openfga_container.get_exposed_port(8080)
    fga_url = f"http://{fga_host}:{fga_port}"

    os.environ["SURREAL_URL"] = surreal_url
    os.environ["SURREAL_NS"] = "autonomyx"
    os.environ["SURREAL_DB"] = "agents"
    os.environ["SURREAL_USER"] = SURREAL_USER
    os.environ["SURREAL_PASS"] = SURREAL_PASS
    os.environ["LITELLM_MASTER_KEY"] = MASTER_KEY
    os.environ["LITELLM_URL"] = "http://litellm-mock:4000"
    os.environ["OPENFGA_URL"] = fga_url
    os.environ["OPENFGA_STORE_ID"] = ""
    os.environ["VICTORIALOGS_URL"] = ""

    return {"surreal_url": surreal_url, "fga_url": fga_url}


@pytest.fixture(scope="session")
def app(setup_env):
    import importlib
    import agent_identity
    import audit
    import blueprints
    import bulk_ops
    import webhooks

    for mod in [agent_identity, audit, blueprints, bulk_ops, webhooks]:
        importlib.reload(mod)

    import main
    importlib.reload(main)
    return main.app


@pytest.fixture(scope="session")
def api(app):
    from fastapi.testclient import TestClient
    return TestClient(app, headers={"Authorization": f"Bearer {MASTER_KEY}"})


@pytest.fixture(autouse=True)
def mock_litellm():
    """Patch LiteLLM functions — let SurrealDB hit real containers."""
    mock_create = AsyncMock(return_value={"key": "sk-integration-test"})
    mock_delete = AsyncMock(return_value=True)
    mock_revoke_by_alias = AsyncMock(return_value=True)
    with patch("agent_identity._create_litellm_key", mock_create), \
         patch("agent_identity._delete_litellm_key", mock_delete), \
         patch("agent_identity._revoke_litellm_key_by_alias", mock_revoke_by_alias):
        yield {"create": mock_create, "delete": mock_delete, "revoke_alias": mock_revoke_by_alias}


# ── Health ───────────────────────────────────────────────────────────────

def test_health(api):
    r = api.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Agent CRUD against real SurrealDB ────────────────────────────────────

def test_create_agent_real_surreal(api):
    name = f"integ-{uuid.uuid4().hex[:8]}"
    r = api.post("/agents/create", json={
        "agent_name": name,
        "sponsor_id": "integration@test.com",
        "tenant_id": "test-tenant",
        "agent_type": "ephemeral",
        "ttl_hours": 1,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "active"
    assert data["litellm_key"] == "sk-integration-test"
    assert data["agent_name"] == name


def test_full_lifecycle_real_surreal(api):
    name = f"lifecycle-{uuid.uuid4().hex[:8]}"

    create = api.post("/agents/create", json={
        "agent_name": name,
        "sponsor_id": "integration@test.com",
        "tenant_id": "test-tenant",
    })
    assert create.status_code == 200
    aid = create.json()["agent_id"]

    get = api.get(f"/agents/{aid}")
    assert get.status_code == 200
    assert get.json()["agent_name"] == name

    suspend = api.post(f"/agents/{aid}/suspend")
    assert suspend.status_code == 200
    assert suspend.json()["status"] == "suspended"

    reactivate = api.post(f"/agents/{aid}/reactivate")
    assert reactivate.status_code == 200
    assert "litellm_key" in reactivate.json()

    rotate = api.post(f"/agents/{aid}/rotate")
    assert rotate.status_code == 200
    assert "litellm_key" in rotate.json()

    revoke = api.delete(f"/agents/{aid}")
    assert revoke.status_code == 200
    assert revoke.json()["status"] == "revoked"

    revoke_again = api.delete(f"/agents/{aid}")
    assert revoke_again.status_code == 409


def test_list_agents_real_surreal(api):
    api.post("/agents/create", json={
        "agent_name": f"list-{uuid.uuid4().hex[:8]}",
        "sponsor_id": "integration@test.com",
        "tenant_id": "test-tenant",
    })
    r = api.get("/agents")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_list_agents_filter_by_tenant(api):
    api.post("/agents/create", json={
        "agent_name": f"filter-{uuid.uuid4().hex[:8]}",
        "sponsor_id": "integration@test.com",
        "tenant_id": "tenant-filter-test",
    })
    r = api.get("/agents?tenant_id=tenant-filter-test")
    assert r.status_code == 200
    agents = r.json()
    assert all(a["tenant_id"] == "tenant-filter-test" for a in agents)


def test_get_agent_not_found(api):
    r = api.get("/agents/nonexistent-uuid")
    assert r.status_code == 404


# ── Blueprints against real SurrealDB ────────────────────────────────────

def test_blueprint_crud_real_surreal(api):
    name = f"bp-{uuid.uuid4().hex[:8]}"
    create = api.post("/blueprints/create", json={
        "name": name,
        "description": "Integration test blueprint",
        "default_models": ["ollama/qwen3:30b-a3b"],
        "owner_id": "integration@test.com",
    })
    assert create.status_code == 200
    bid = create.json()["blueprint_id"]

    get = api.get(f"/blueprints/{bid}")
    assert get.status_code == 200
    assert get.json()["name"] == name

    list_bp = api.get("/blueprints/")
    assert list_bp.status_code == 200
    assert any(bp["blueprint_id"] == bid for bp in list_bp.json())


# ── Audit against real SurrealDB ─────────────────────────────────────────

def test_audit_log_queryable(api):
    r = api.get("/audit/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_audit_filter_by_tenant(api):
    r = api.get("/audit/?tenant_id=test-tenant")
    assert r.status_code == 200


def test_audit_agent_trail(api):
    r = api.get("/audit/agent/nonexistent-id")
    assert r.status_code == 200
    assert r.json() == []


# ── Webhooks (in-memory, no container needed) ────────────────────────────

def test_webhook_register_and_list(api):
    reg = api.post("/webhooks/register", json={
        "url": "https://example.com/hook",
        "events": ["agent.created"],
    })
    assert reg.status_code == 200

    hooks = api.get("/webhooks/")
    assert hooks.status_code == 200
    assert len(hooks.json()) >= 1


# ── Bulk ops ─────────────────────────────────────────────────────────────

def test_bulk_suspend_empty(api):
    r = api.post("/bulk/suspend", json={"agent_ids": []})
    assert r.status_code == 200
    assert r.json()["succeeded"] == []


# ── Auth enforcement ─────────────────────────────────────────────────────

def test_no_auth_rejected(app):
    from fastapi.testclient import TestClient
    unauthed = TestClient(app)
    r = unauthed.get("/audit/")
    assert r.status_code == 401


def test_wrong_auth_rejected(app):
    from fastapi.testclient import TestClient
    bad_auth = TestClient(app, headers={"Authorization": "Bearer wrong-key"})
    r = bad_auth.get("/audit/")
    assert r.status_code == 401
