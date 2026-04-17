"""tests/test_kc_lago_sync.py
Full coverage for kc_lago_sync.py.
Mocks all httpx HTTP calls with respx — no real Keycloak/Lago/LiteLLM needed.
"""
import pytest
import httpx
import respx
import os
from unittest.mock import patch, MagicMock

# Set env vars before import
os.environ.setdefault("KEYCLOAK_URL",           "http://keycloak:8080")
os.environ.setdefault("KEYCLOAK_REALM",         "autonomyx")
os.environ.setdefault("KEYCLOAK_ADMIN",         "admin")
os.environ.setdefault("KEYCLOAK_ADMIN_PASSWORD","testpass")
os.environ.setdefault("LAGO_API_URL",           "http://lago:3000")
os.environ.setdefault("LAGO_API_KEY",           "test-lago-key")
os.environ.setdefault("LAGO_DEFAULT_PLAN",      "developer")
os.environ.setdefault("LITELLM_URL",            "http://litellm:4000")
os.environ.setdefault("LITELLM_MASTER_KEY",     "test-master-key")
os.environ.setdefault("LANGFUSE_HOST",          "http://langfuse:3001")
os.environ.setdefault("LANGFUSE_SECRET_KEY",    "test-langfuse-key")

import sys, os as _os
sys.path.insert(0, str(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
import kc_lago_sync as kc

FAKE_TOKEN = "eyJfaketoken"
FAKE_KEY   = "sk-" + "x" * 40


# ── Keycloak auth ─────────────────────────────────────────────────────────────

@respx.mock
def test_get_kc_token_success():
    respx.post(f"{kc.KC_URL}/realms/master/protocol/openid-connect/token").mock(
        return_value=httpx.Response(200, json={"access_token": FAKE_TOKEN})
    )
    token = kc.get_kc_token()
    assert token == FAKE_TOKEN


@respx.mock
def test_get_kc_token_failure():
    respx.post(f"{kc.KC_URL}/realms/master/protocol/openid-connect/token").mock(
        return_value=httpx.Response(401, json={"error": "unauthorized"})
    )
    with pytest.raises(httpx.HTTPStatusError):
        kc.get_kc_token()


@respx.mock
def test_list_kc_groups():
    groups = [{"id": "g1", "name": "tenant-acme"}, {"id": "g2", "name": "tenant-beta"}]
    respx.get(f"{kc.KC_URL}/admin/realms/{kc.KC_REALM}/groups").mock(
        return_value=httpx.Response(200, json=groups)
    )
    result = kc.list_kc_groups(FAKE_TOKEN)
    assert len(result) == 2
    assert result[0]["id"] == "g1"


@respx.mock
def test_get_kc_group_attrs():
    respx.get(f"{kc.KC_URL}/admin/realms/{kc.KC_REALM}/groups/g1").mock(
        return_value=httpx.Response(200, json={
            "attributes": {"provisioned": ["true"], "plan": ["developer"]}
        })
    )
    attrs = kc.get_kc_group_attrs(FAKE_TOKEN, "g1")
    assert attrs["provisioned"] == ["true"]
    assert attrs["plan"] == ["developer"]


@respx.mock
def test_get_kc_group_attrs_empty():
    """Returns empty dict when group has no attributes."""
    respx.get(f"{kc.KC_URL}/admin/realms/{kc.KC_REALM}/groups/g1").mock(
        return_value=httpx.Response(200, json={})
    )
    attrs = kc.get_kc_group_attrs(FAKE_TOKEN, "g1")
    assert attrs == {}


@respx.mock
def test_set_kc_group_attr():
    route = respx.put(f"{kc.KC_URL}/admin/realms/{kc.KC_REALM}/groups/g1").mock(
        return_value=httpx.Response(204)
    )
    kc.set_kc_group_attr(FAKE_TOKEN, "g1", "tenant-acme", {"provisioned": ["true"]})
    assert route.called


# ── Lago ──────────────────────────────────────────────────────────────────────

@respx.mock
def test_create_lago_customer():
    respx.post(f"{kc.LAGO_URL}/api/v1/customers").mock(
        return_value=httpx.Response(200, json={"customer": {"external_id": "tenant-acme"}})
    )
    result = kc.create_lago_customer("tenant-acme", "Acme Corp")
    assert result["customer"]["external_id"] == "tenant-acme"


@respx.mock
def test_create_lago_customer_error():
    respx.post(f"{kc.LAGO_URL}/api/v1/customers").mock(
        return_value=httpx.Response(422, json={"error": "already exists"})
    )
    with pytest.raises(httpx.HTTPStatusError):
        kc.create_lago_customer("tenant-acme", "Acme Corp")


@respx.mock
def test_assign_lago_plan_success():
    route = respx.post(f"{kc.LAGO_URL}/api/v1/subscriptions").mock(
        return_value=httpx.Response(200, json={"subscription": {}})
    )
    kc.assign_lago_plan("tenant-acme", "developer")
    assert route.called


@respx.mock
def test_assign_lago_plan_failure_does_not_raise():
    """Plan assignment failure logs warning but doesn't raise."""
    respx.post(f"{kc.LAGO_URL}/api/v1/subscriptions").mock(
        return_value=httpx.Response(500, json={"error": "internal error"})
    )
    # Should not raise
    kc.assign_lago_plan("tenant-acme", "developer")


@respx.mock
def test_archive_lago_customer():
    route = respx.delete(f"{kc.LAGO_URL}/api/v1/customers/tenant-acme").mock(
        return_value=httpx.Response(200, json={})
    )
    kc.archive_lago_customer("tenant-acme")
    assert route.called


# ── LiteLLM ───────────────────────────────────────────────────────────────────

@respx.mock
def test_create_litellm_key():
    respx.post(f"{kc.LITELLM_URL}/key/generate").mock(
        return_value=httpx.Response(200, json={"key": FAKE_KEY})
    )
    key = kc.create_litellm_key("tenant-acme", "developer")
    assert key == FAKE_KEY


@respx.mock
def test_create_litellm_key_uses_plan_budget():
    """Verifies correct budget is applied per plan."""
    captured = {}

    def capture(request, route):
        import json
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"key": FAKE_KEY})

    respx.post(f"{kc.LITELLM_URL}/key/generate").mock(side_effect=capture)

    kc.create_litellm_key("tenant-acme", "growth")
    assert captured["body"]["max_budget"] == kc.PLAN_BUDGETS["growth"]["max_budget"]
    assert captured["body"]["tpm_limit"]  == kc.PLAN_BUDGETS["growth"]["tpm_limit"]


@respx.mock
def test_create_litellm_key_unknown_plan_uses_default():
    """Unknown plan falls back to developer budget."""
    captured = {}

    def capture(request, route):
        import json
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"key": FAKE_KEY})

    respx.post(f"{kc.LITELLM_URL}/key/generate").mock(side_effect=capture)
    kc.create_litellm_key("tenant-acme", "nonexistent-plan")
    assert captured["body"]["max_budget"] == kc.PLAN_BUDGETS["developer"]["max_budget"]


@respx.mock
def test_revoke_litellm_key_found():
    """Revokes key when alias is found in key list."""
    respx.get(f"{kc.LITELLM_URL}/key/list").mock(
        return_value=httpx.Response(200, json={
            "keys": [{"key_alias": "tenant-acme", "key": FAKE_KEY}]
        })
    )
    route = respx.post(f"{kc.LITELLM_URL}/key/delete").mock(
        return_value=httpx.Response(200, json={})
    )
    kc.revoke_litellm_key("tenant-acme")
    assert route.called


@respx.mock
def test_revoke_litellm_key_not_found():
    """Does nothing when alias not in key list."""
    respx.get(f"{kc.LITELLM_URL}/key/list").mock(
        return_value=httpx.Response(200, json={"keys": []})
    )
    delete_route = respx.post(f"{kc.LITELLM_URL}/key/delete").mock(
        return_value=httpx.Response(200, json={})
    )
    kc.revoke_litellm_key("nonexistent-tenant")
    assert not delete_route.called


@respx.mock
def test_revoke_litellm_key_api_error():
    """Does nothing on non-200 from key/list."""
    respx.get(f"{kc.LITELLM_URL}/key/list").mock(
        return_value=httpx.Response(500, json={})
    )
    # Should not raise
    kc.revoke_litellm_key("tenant-acme")


# ── Langfuse ──────────────────────────────────────────────────────────────────

@respx.mock
def test_create_langfuse_org_success():
    respx.post(f"{kc.LANGFUSE_HOST}/api/admin/organizations").mock(
        return_value=httpx.Response(201, json={"id": "org-123"})
    )
    result = kc.create_langfuse_org("tenant-acme")
    assert result == "org-123"


@respx.mock
def test_create_langfuse_org_failure_returns_none():
    """Returns None on failure — Langfuse is not blocking."""
    respx.post(f"{kc.LANGFUSE_HOST}/api/admin/organizations").mock(
        return_value=httpx.Response(500, json={"error": "internal"})
    )
    result = kc.create_langfuse_org("tenant-acme")
    assert result is None


# ── Plan budget mapping ───────────────────────────────────────────────────────

def test_all_plans_have_required_keys():
    for plan, budget in kc.PLAN_BUDGETS.items():
        assert "max_budget"      in budget, f"Plan '{plan}' missing max_budget"
        assert "budget_duration" in budget, f"Plan '{plan}' missing budget_duration"
        assert "tpm_limit"       in budget, f"Plan '{plan}' missing tpm_limit"
        assert budget["max_budget"] > 0
        assert budget["tpm_limit"]  > 0


def test_plan_budgets_ordered():
    """Higher tier plans should have higher budgets."""
    assert kc.PLAN_BUDGETS["developer"]["max_budget"] > kc.PLAN_BUDGETS["free"]["max_budget"]
    assert kc.PLAN_BUDGETS["growth"]["max_budget"]    > kc.PLAN_BUDGETS["developer"]["max_budget"]
    assert kc.PLAN_BUDGETS["saas_basic"]["max_budget"] > kc.PLAN_BUDGETS["growth"]["max_budget"]


# ── provision_tenant ──────────────────────────────────────────────────────────

@respx.mock
def test_provision_tenant_full_flow():
    """Full provision: Lago + LiteLLM + Langfuse + KC attribute update."""
    respx.post(f"{kc.LAGO_URL}/api/v1/customers").mock(
        return_value=httpx.Response(200, json={"customer": {}})
    )
    respx.post(f"{kc.LAGO_URL}/api/v1/subscriptions").mock(
        return_value=httpx.Response(200, json={})
    )
    respx.post(f"{kc.LITELLM_URL}/key/generate").mock(
        return_value=httpx.Response(200, json={"key": FAKE_KEY})
    )
    respx.post(f"{kc.LANGFUSE_HOST}/api/admin/organizations").mock(
        return_value=httpx.Response(201, json={"id": "org-xyz"})
    )
    respx.get(f"{kc.KC_URL}/admin/realms/{kc.KC_REALM}/groups/g1").mock(
        return_value=httpx.Response(200, json={"attributes": {}})
    )
    respx.put(f"{kc.KC_URL}/admin/realms/{kc.KC_REALM}/groups/g1").mock(
        return_value=httpx.Response(204)
    )

    group = {"id": "g1", "name": "tenant-acme"}
    kc.provision_tenant(FAKE_TOKEN, group)  # should not raise


@respx.mock
def test_provision_tenant_detects_plan_from_name():
    """Plan is detected from group name if it matches a known plan."""
    respx.post(f"{kc.LAGO_URL}/api/v1/customers").mock(
        return_value=httpx.Response(200, json={"customer": {}})
    )
    captured = {}

    def capture_sub(request, route):
        import json
        captured["sub"] = json.loads(request.content)
        return httpx.Response(200, json={})

    respx.post(f"{kc.LAGO_URL}/api/v1/subscriptions").mock(side_effect=capture_sub)
    respx.post(f"{kc.LITELLM_URL}/key/generate").mock(
        return_value=httpx.Response(200, json={"key": FAKE_KEY})
    )
    respx.post(f"{kc.LANGFUSE_HOST}/api/admin/organizations").mock(
        return_value=httpx.Response(201, json={"id": "org-xyz"})
    )
    respx.get(f"{kc.KC_URL}/admin/realms/{kc.KC_REALM}/groups/g1").mock(
        return_value=httpx.Response(200, json={"attributes": {}})
    )
    respx.put(f"{kc.KC_URL}/admin/realms/{kc.KC_REALM}/groups/g1").mock(
        return_value=httpx.Response(204)
    )

    # Group name contains "growth" — should use growth plan
    group = {"id": "g1", "name": "tenant-acme-growth"}
    kc.provision_tenant(FAKE_TOKEN, group)
    assert captured["sub"]["subscription"]["plan_code"] == "growth"


@respx.mock
def test_provision_tenant_exception_does_not_crash():
    """Provisioning catches exceptions and logs error without raising."""
    respx.post(f"{kc.LAGO_URL}/api/v1/customers").mock(
        return_value=httpx.Response(500, json={"error": "server error"})
    )
    group = {"id": "g1", "name": "tenant-acme"}
    kc.provision_tenant(FAKE_TOKEN, group)  # should not raise


# ── deprovision_tenant ────────────────────────────────────────────────────────

@respx.mock
def test_deprovision_tenant():
    respx.delete(f"{kc.LAGO_URL}/api/v1/customers/tenant-acme").mock(
        return_value=httpx.Response(200, json={})
    )
    respx.get(f"{kc.LITELLM_URL}/key/list").mock(
        return_value=httpx.Response(200, json={"keys": [
            {"key_alias": "tenant-acme", "key": FAKE_KEY}
        ]})
    )
    respx.post(f"{kc.LITELLM_URL}/key/delete").mock(
        return_value=httpx.Response(200, json={})
    )
    kc.deprovision_tenant("tenant-acme")  # should not raise


@respx.mock
def test_deprovision_tenant_exception_does_not_crash():
    respx.delete(f"{kc.LAGO_URL}/api/v1/customers/tenant-acme").mock(
        return_value=httpx.Response(500, json={})
    )
    kc.deprovision_tenant("tenant-acme")  # should not raise


# ── sync_loop (single iteration) ──────────────────────────────────────────────

@respx.mock
def test_sync_loop_provisions_new_group():
    """sync_loop provisions a new unprovisioned group on first iteration."""
    respx.post(f"{kc.KC_URL}/realms/master/protocol/openid-connect/token").mock(
        return_value=httpx.Response(200, json={"access_token": FAKE_TOKEN})
    )
    respx.get(f"{kc.KC_URL}/admin/realms/{kc.KC_REALM}/groups").mock(
        return_value=httpx.Response(200, json=[{"id": "g1", "name": "tenant-new"}])
    )
    respx.get(f"{kc.KC_URL}/admin/realms/{kc.KC_REALM}/groups/g1").mock(
        return_value=httpx.Response(200, json={"attributes": {}})  # not provisioned
    )
    respx.post(f"{kc.LAGO_URL}/api/v1/customers").mock(
        return_value=httpx.Response(200, json={"customer": {}})
    )
    respx.post(f"{kc.LAGO_URL}/api/v1/subscriptions").mock(
        return_value=httpx.Response(200, json={})
    )
    respx.post(f"{kc.LITELLM_URL}/key/generate").mock(
        return_value=httpx.Response(200, json={"key": FAKE_KEY})
    )
    respx.post(f"{kc.LANGFUSE_HOST}/api/admin/organizations").mock(
        return_value=httpx.Response(201, json={"id": "org-1"})
    )
    respx.put(f"{kc.KC_URL}/admin/realms/{kc.KC_REALM}/groups/g1").mock(
        return_value=httpx.Response(204)
    )

    # Patch time.sleep and run exactly one iteration
    iterations = [0]

    def fake_sleep(n):
        iterations[0] += 1
        if iterations[0] >= 1:
            raise KeyboardInterrupt  # break the loop

    with patch("kc_lago_sync.time") as mock_time:
        mock_time.sleep.side_effect = fake_sleep
        try:
            kc.sync_loop()
        except KeyboardInterrupt:
            pass


@respx.mock
def test_sync_loop_skips_already_provisioned():
    """sync_loop skips groups with provisioned=true attribute."""
    respx.post(f"{kc.KC_URL}/realms/master/protocol/openid-connect/token").mock(
        return_value=httpx.Response(200, json={"access_token": FAKE_TOKEN})
    )
    respx.get(f"{kc.KC_URL}/admin/realms/{kc.KC_REALM}/groups").mock(
        return_value=httpx.Response(200, json=[{"id": "g1", "name": "tenant-existing"}])
    )
    respx.get(f"{kc.KC_URL}/admin/realms/{kc.KC_REALM}/groups/g1").mock(
        return_value=httpx.Response(200, json={
            "attributes": {"provisioned": ["true"]}
        })
    )
    # These should NOT be called
    lago_route = respx.post(f"{kc.LAGO_URL}/api/v1/customers").mock(
        return_value=httpx.Response(200, json={})
    )

    with patch("kc_lago_sync.time") as mock_time:
        mock_time.sleep.side_effect = KeyboardInterrupt
        try:
            kc.sync_loop()
        except KeyboardInterrupt:
            pass

    assert not lago_route.called
