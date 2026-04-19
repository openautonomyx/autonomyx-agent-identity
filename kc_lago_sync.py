"""Keycloak/Lago/LiteLLM/Langfuse tenant provisioning helpers."""
import logging
import os
import time

import httpx

log = logging.getLogger("kc_lago_sync")

KC_URL = os.environ.get("KEYCLOAK_URL", "http://keycloak:8080")
KC_REALM = os.environ.get("KEYCLOAK_REALM", "autonomyx")
KC_ADMIN = os.environ.get("KEYCLOAK_ADMIN", "admin")
KC_ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "")

LAGO_URL = os.environ.get("LAGO_API_URL", "http://lago:3000")
LAGO_API_KEY = os.environ.get("LAGO_API_KEY", "")
LAGO_DEFAULT_PLAN = os.environ.get("LAGO_DEFAULT_PLAN", "developer")

LITELLM_URL = os.environ.get("LITELLM_URL", "http://litellm:4000")
LITELLM_MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "")

LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")

PLAN_BUDGETS = {
    "free": {"max_budget": 2.0, "budget_duration": "30d", "tpm_limit": 5000},
    "developer": {"max_budget": 10.0, "budget_duration": "30d", "tpm_limit": 20000},
    "growth": {"max_budget": 50.0, "budget_duration": "30d", "tpm_limit": 60000},
    "saas_basic": {"max_budget": 150.0, "budget_duration": "30d", "tpm_limit": 120000},
}


def get_kc_token() -> str:
    r = httpx.post(
        f"{KC_URL}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": KC_ADMIN,
            "password": KC_ADMIN_PASSWORD,
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _kc_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def list_kc_groups(token: str):
    r = httpx.get(f"{KC_URL}/admin/realms/{KC_REALM}/groups", headers=_kc_headers(token), timeout=10)
    r.raise_for_status()
    return r.json()


def get_kc_group_attrs(token: str, group_id: str):
    r = httpx.get(f"{KC_URL}/admin/realms/{KC_REALM}/groups/{group_id}", headers=_kc_headers(token), timeout=10)
    r.raise_for_status()
    return r.json().get("attributes", {})


def set_kc_group_attr(token: str, group_id: str, name: str, attrs: dict):
    r = httpx.put(
        f"{KC_URL}/admin/realms/{KC_REALM}/groups/{group_id}",
        headers=_kc_headers(token),
        json={"name": name, "attributes": attrs},
        timeout=10,
    )
    r.raise_for_status()


def create_lago_customer(tenant_id: str, name: str):
    r = httpx.post(
        f"{LAGO_URL}/api/v1/customers",
        headers={"Authorization": f"Bearer {LAGO_API_KEY}", "Content-Type": "application/json"},
        json={"customer": {"external_id": tenant_id, "name": name}},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def assign_lago_plan(tenant_id: str, plan: str):
    r = httpx.post(
        f"{LAGO_URL}/api/v1/subscriptions",
        headers={"Authorization": f"Bearer {LAGO_API_KEY}", "Content-Type": "application/json"},
        json={"subscription": {"external_customer_id": tenant_id, "plan_code": plan or LAGO_DEFAULT_PLAN}},
        timeout=10,
    )
    if r.status_code >= 400:
        log.warning("Failed to assign Lago plan for %s: %s", tenant_id, r.text)


def archive_lago_customer(tenant_id: str):
    r = httpx.delete(
        f"{LAGO_URL}/api/v1/customers/{tenant_id}",
        headers={"Authorization": f"Bearer {LAGO_API_KEY}"},
        timeout=10,
    )
    r.raise_for_status()


def create_litellm_key(tenant_id: str, plan: str):
    resolved = PLAN_BUDGETS.get(plan, PLAN_BUDGETS["developer"])
    r = httpx.post(
        f"{LITELLM_URL}/key/generate",
        headers={"Authorization": f"Bearer {LITELLM_MASTER_KEY}", "Content-Type": "application/json"},
        json={
            "key_alias": tenant_id,
            "max_budget": resolved["max_budget"],
            "budget_duration": resolved["budget_duration"],
            "tpm_limit": resolved["tpm_limit"],
            "models": ["*"],
            "metadata": {"tenant_id": tenant_id, "plan": plan},
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["key"]


def revoke_litellm_key(tenant_id: str):
    r = httpx.get(f"{LITELLM_URL}/key/list", headers={"Authorization": f"Bearer {LITELLM_MASTER_KEY}"}, timeout=10)
    if r.status_code != 200:
        return
    for key in r.json().get("keys", []):
        if key.get("key_alias") == tenant_id:
            httpx.post(
                f"{LITELLM_URL}/key/delete",
                headers={"Authorization": f"Bearer {LITELLM_MASTER_KEY}", "Content-Type": "application/json"},
                json={"keys": [key.get("key")]},
                timeout=10,
            )
            return


def create_langfuse_org(tenant_id: str):
    if not LANGFUSE_HOST or not LANGFUSE_SECRET_KEY:
        return None
    r = httpx.post(
        f"{LANGFUSE_HOST}/api/admin/organizations",
        headers={"Authorization": f"Bearer {LANGFUSE_SECRET_KEY}", "Content-Type": "application/json"},
        json={"name": tenant_id},
        timeout=10,
    )
    if r.status_code in (200, 201):
        return r.json().get("id")
    return None


def _detect_plan(group_name: str) -> str:
    n = (group_name or '').lower()
    for plan in PLAN_BUDGETS:
        if plan in n:
            return plan
    return LAGO_DEFAULT_PLAN


def provision_tenant(token: str, group: dict):
    try:
        tenant_name = group.get('name', '')
        gid = group.get('id', '')
        plan = _detect_plan(tenant_name)
        create_lago_customer(tenant_name, tenant_name)
        assign_lago_plan(tenant_name, plan)
        create_litellm_key(tenant_name, plan)
        langfuse_org_id = create_langfuse_org(tenant_name)

        attrs = get_kc_group_attrs(token, gid)
        attrs['provisioned'] = ['true']
        attrs['plan'] = [plan]
        if langfuse_org_id:
            attrs['langfuse_org_id'] = [langfuse_org_id]
        set_kc_group_attr(token, gid, tenant_name, attrs)
    except Exception as exc:
        log.error('provision_tenant failed for %s: %s', group.get('name'), exc)


def deprovision_tenant(tenant_name: str):
    try:
        archive_lago_customer(tenant_name)
        revoke_litellm_key(tenant_name)
    except Exception as exc:
        log.error('deprovision_tenant failed for %s: %s', tenant_name, exc)


def sync_loop(interval_seconds: int = 60):
    while True:
        token = get_kc_token()
        groups = list_kc_groups(token)
        for group in groups:
            attrs = get_kc_group_attrs(token, group.get('id', ''))
            if attrs.get('provisioned', ['false'])[0] == 'true':
                continue
            provision_tenant(token, group)
        time.sleep(interval_seconds)
