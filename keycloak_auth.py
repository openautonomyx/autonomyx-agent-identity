"""
keycloak_auth.py — Keycloak JWT verification for Agent Identity API

Verifies Keycloak-issued JWTs for human authentication.
Agents don't use Keycloak — they use LiteLLM Virtual Keys.

Usage:
    from keycloak_auth import get_current_user, KeycloakUser

    @router.post("/agents/create")
    async def create_agent(user: KeycloakUser = Depends(get_current_user)):
        # user.sub = Keycloak user ID
        # user.email = chinmay@openautonomyx.com
        # user.groups = ["operators"]
"""

import os
import httpx
from typing import Optional, List
from dataclasses import dataclass
from fastapi import Header, HTTPException

KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "https://auth.unboxd.cloud")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "autonomyx")
JWKS_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
LITELLM_MASTER = os.environ.get("LITELLM_MASTER_KEY", "")

# Cache JWKS keys
_jwks_cache = None


@dataclass
class KeycloakUser:
    sub: str
    email: str
    preferred_username: str
    groups: List[str]
    realm_access: dict


async def _get_jwks():
    """Fetch JWKS from Keycloak (cached)."""
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(JWKS_URL)
            r.raise_for_status()
            _jwks_cache = r.json()
            return _jwks_cache
    except Exception:
        return None


async def verify_jwt(token: str) -> Optional[dict]:
    """
    Verify a Keycloak JWT token.
    For production: use python-jose or PyJWT with JWKS verification.
    For now: decode and validate via Keycloak userinfo endpoint.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/userinfo",
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 200:
                return r.json()
            return None
    except Exception:
        return None


async def get_current_user(
    authorization: str = Header(None),
) -> KeycloakUser:
    """
    Extract and verify user from Authorization header.
    Accepts:
      - Keycloak JWT: Bearer eyJ... → verified via Keycloak userinfo
      - Master key: Bearer sk-autonomyx-... → returns admin user
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    token = authorization.replace("Bearer ", "").strip()

    # Master key bypass (for CLI/API access without browser login)
    if token == LITELLM_MASTER:
        return KeycloakUser(
            sub="admin",
            email="admin@openautonomyx.com",
            preferred_username="admin",
            groups=["operators"],
            realm_access={"roles": ["admin"]},
        )

    # Keycloak JWT verification
    userinfo = await verify_jwt(token)
    if not userinfo:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return KeycloakUser(
        sub=userinfo.get("sub", ""),
        email=userinfo.get("email", ""),
        preferred_username=userinfo.get("preferred_username", ""),
        groups=userinfo.get("groups", []),
        realm_access=userinfo.get("realm_access", {}),
    )
