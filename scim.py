"""
scim.py — SCIM 2.0 Server (RFC 7644)

Enables any SCIM-compatible app to provision/deprovision
users and agents through the Autonomyx Identity system.

Endpoints:
  GET    /scim/v2/Users
  POST   /scim/v2/Users
  GET    /scim/v2/Users/{id}
  PUT    /scim/v2/Users/{id}
  PATCH  /scim/v2/Users/{id}
  DELETE /scim/v2/Users/{id}
  GET    /scim/v2/Groups
  POST   /scim/v2/Groups
  GET    /scim/v2/ServiceProviderConfig
  GET    /scim/v2/Schemas
  GET    /scim/v2/ResourceTypes
"""

import os, uuid, httpx
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/scim/v2", tags=["SCIM 2.0"])

SURREAL_URL = os.environ.get("SURREAL_URL", "")
SURREAL_NS = os.environ.get("SURREAL_NS", "autonomyx")
SURREAL_DB = os.environ.get("SURREAL_DB", "agents")
SURREAL_USER = os.environ.get("SURREAL_USER", "")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "")
LITELLM_MASTER = os.environ.get("LITELLM_MASTER_KEY", "")
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "autonomyx")
KEYCLOAK_ADMIN = os.environ.get("KEYCLOAK_ADMIN", "admin")
KEYCLOAK_ADMIN_PASS = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "")


def _require_auth(authorization: Optional[str]):
    token = (authorization or "").replace("Bearer ", "").strip()
    if token != LITELLM_MASTER:
        raise HTTPException(status_code=401, detail="Unauthorized")


async def _surreal_query(query: str, vars: dict = None):
    if not SURREAL_URL:
        return None
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{SURREAL_URL}/rpc",
            headers={
                "surreal-ns": SURREAL_NS,
                "surreal-db": SURREAL_DB,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            auth=(SURREAL_USER, SURREAL_PASS),
            json={"id": 1, "method": "query", "params": [query, vars or {}]},
        )
        return r.json().get("result", [])


async def _keycloak_token():
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": KEYCLOAK_ADMIN,
                "password": KEYCLOAK_ADMIN_PASS,
            },
        )
        if r.status_code == 200:
            return r.json()["access_token"]
    return None


def _to_scim_user(record: dict, is_agent: bool = False) -> dict:
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": record.get("agent_id") or record.get("id", ""),
        "userName": record.get("agent_name") or record.get("username", ""),
        "displayName": record.get("agent_name") or record.get("firstName", ""),
        "active": record.get("status", "active") == "active" if is_agent else record.get("enabled", True),
        "emails": [{"value": record.get("email", ""), "primary": True}] if record.get("email") else [],
        "meta": {
            "resourceType": "User",
            "created": record.get("created_at", ""),
            "lastModified": record.get("last_active_at", record.get("created_at", "")),
        },
        "urn:ietf:params:scim:schemas:extension:autonomyx:2.0:User": {
            "entityType": "agent" if is_agent else "human",
            "tenantId": record.get("tenant_id", ""),
            "sponsorId": record.get("sponsor_id", ""),
            "agentType": record.get("agent_type", ""),
        },
    }


# ── ServiceProviderConfig ─────────────────────────────────────────────────

@router.get("/ServiceProviderConfig")
async def service_provider_config():
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "documentationUri": "https://docs.openautonomyx.com/scim",
        "patch": {"supported": True},
        "bulk": {"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
        "filter": {"supported": True, "maxResults": 200},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {
                "type": "oauthbearertoken",
                "name": "OAuth Bearer Token",
                "description": "Authentication using Bearer token",
            }
        ],
    }


@router.get("/Schemas")
async def schemas():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "Resources": [
            {
                "id": "urn:ietf:params:scim:schemas:core:2.0:User",
                "name": "User",
                "description": "Human or Agent identity",
            },
            {
                "id": "urn:ietf:params:scim:schemas:core:2.0:Group",
                "name": "Group",
                "description": "Tenant / Organization",
            },
        ],
    }


@router.get("/ResourceTypes")
async def resource_types():
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "Resources": [
            {
                "id": "User",
                "name": "User",
                "endpoint": "/scim/v2/Users",
                "schema": "urn:ietf:params:scim:schemas:core:2.0:User",
            },
            {
                "id": "Group",
                "name": "Group",
                "endpoint": "/scim/v2/Groups",
                "schema": "urn:ietf:params:scim:schemas:core:2.0:Group",
            },
        ],
    }


# ── Users (Agents + Humans) ──────────────────────────────────────────────

@router.get("/Users")
async def list_users(
    filter: Optional[str] = Query(None),
    startIndex: int = Query(1),
    count: int = Query(100),
    authorization: Optional[str] = Header(None),
):
    _require_auth(authorization)

    resources = []

    result = await _surreal_query(
        "SELECT * FROM agents ORDER BY created_at DESC LIMIT $count;",
        {"count": count},
    )
    if result and result[0].get("result"):
        for a in result[0]["result"]:
            resources.append(_to_scim_user(a, is_agent=True))

    kc_token = await _keycloak_token()
    if kc_token:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users",
                headers={"Authorization": f"Bearer {kc_token}"},
                params={"max": count},
            )
            if r.status_code == 200:
                for u in r.json():
                    resources.append(_to_scim_user(u, is_agent=False))

    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(resources),
        "startIndex": startIndex,
        "itemsPerPage": count,
        "Resources": resources,
    }


@router.get("/Users/{user_id}")
async def get_user(user_id: str, authorization: Optional[str] = Header(None)):
    _require_auth(authorization)

    result = await _surreal_query(
        "SELECT * FROM agents WHERE agent_id = $id LIMIT 1;",
        {"id": user_id},
    )
    if result and result[0].get("result"):
        return _to_scim_user(result[0]["result"][0], is_agent=True)

    kc_token = await _keycloak_token()
    if kc_token:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}",
                headers={"Authorization": f"Bearer {kc_token}"},
            )
            if r.status_code == 200:
                return _to_scim_user(r.json(), is_agent=False)

    raise HTTPException(status_code=404, detail="User not found")


@router.post("/Users", status_code=201)
async def create_user(request: Request, authorization: Optional[str] = Header(None)):
    _require_auth(authorization)
    body = await request.json()

    ext = body.get("urn:ietf:params:scim:schemas:extension:autonomyx:2.0:User", {})
    entity_type = ext.get("entityType", "human")

    if entity_type == "agent":
        from agent_identity import create_agent
        from pydantic import BaseModel

        class FakeReq:
            agent_name = body.get("userName", "")
            agent_type = ext.get("agentType", "workflow")
            sponsor_id = ext.get("sponsorId", "scim-provisioned")
            owner_ids = []
            manager_id = None
            blueprint_id = None
            tenant_id = ext.get("tenantId", "")
            allowed_models = None
            budget_limit = None
            tpm_limit = 10000
            ttl_hours = None
            metadata = {"provisioned_via": "scim"}

        result = await create_agent(FakeReq(), f"Bearer {LITELLM_MASTER}")
        return _to_scim_user(result if isinstance(result, dict) else result.__dict__, is_agent=True)
    else:
        kc_token = await _keycloak_token()
        if not kc_token:
            raise HTTPException(status_code=502, detail="Keycloak unavailable")

        emails = body.get("emails", [])
        email = emails[0]["value"] if emails else ""

        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users",
                headers={"Authorization": f"Bearer {kc_token}", "Content-Type": "application/json"},
                json={
                    "username": body.get("userName", ""),
                    "email": email,
                    "firstName": body.get("displayName", ""),
                    "enabled": body.get("active", True),
                },
            )
            if r.status_code == 201:
                location = r.headers.get("Location", "")
                uid = location.split("/")[-1] if location else ""
                return _to_scim_user({"id": uid, "username": body.get("userName"), "email": email})
            raise HTTPException(status_code=r.status_code, detail=r.text)


@router.patch("/Users/{user_id}")
async def patch_user(user_id: str, request: Request, authorization: Optional[str] = Header(None)):
    _require_auth(authorization)
    body = await request.json()

    for op in body.get("Operations", []):
        if op.get("path") == "active" and op.get("value") is False:
            result = await _surreal_query(
                "SELECT * FROM agents WHERE agent_id = $id LIMIT 1;",
                {"id": user_id},
            )
            if result and result[0].get("result"):
                from agent_identity import suspend_agent
                await suspend_agent(user_id, f"Bearer {LITELLM_MASTER}")
                return _to_scim_user({**result[0]["result"][0], "status": "suspended"}, is_agent=True)

            kc_token = await _keycloak_token()
            if kc_token:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.put(
                        f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}",
                        headers={"Authorization": f"Bearer {kc_token}", "Content-Type": "application/json"},
                        json={"enabled": False},
                    )

    return await get_user(user_id, authorization)


@router.delete("/Users/{user_id}", status_code=204)
async def delete_user(user_id: str, authorization: Optional[str] = Header(None)):
    _require_auth(authorization)

    result = await _surreal_query(
        "SELECT * FROM agents WHERE agent_id = $id LIMIT 1;",
        {"id": user_id},
    )
    if result and result[0].get("result"):
        from agent_identity import revoke_agent
        await revoke_agent(user_id, f"Bearer {LITELLM_MASTER}")
        return

    kc_token = await _keycloak_token()
    if kc_token:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.delete(
                f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}",
                headers={"Authorization": f"Bearer {kc_token}"},
            )
            if r.status_code in (204, 404):
                return

    raise HTTPException(status_code=404, detail="User not found")


# ── Groups (Tenants) ─────────────────────────────────────────────────────

@router.get("/Groups")
async def list_groups(
    count: int = Query(100),
    authorization: Optional[str] = Header(None),
):
    _require_auth(authorization)

    kc_token = await _keycloak_token()
    groups = []
    if kc_token:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/groups",
                headers={"Authorization": f"Bearer {kc_token}"},
                params={"max": count},
            )
            if r.status_code == 200:
                for g in r.json():
                    groups.append({
                        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
                        "id": g["id"],
                        "displayName": g["name"],
                        "members": [],
                    })

    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(groups),
        "Resources": groups,
    }


@router.post("/Groups", status_code=201)
async def create_group(request: Request, authorization: Optional[str] = Header(None)):
    _require_auth(authorization)
    body = await request.json()

    kc_token = await _keycloak_token()
    if not kc_token:
        raise HTTPException(status_code=502, detail="Keycloak unavailable")

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/groups",
            headers={"Authorization": f"Bearer {kc_token}", "Content-Type": "application/json"},
            json={"name": body.get("displayName", "")},
        )
        if r.status_code == 201:
            location = r.headers.get("Location", "")
            gid = location.split("/")[-1] if location else ""
            return {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
                "id": gid,
                "displayName": body.get("displayName"),
                "members": [],
            }
        raise HTTPException(status_code=r.status_code, detail=r.text)
