"""Tests for keycloak_auth.py"""
import pytest
from unittest.mock import AsyncMock, patch
from keycloak_auth import get_current_user, KeycloakUser

@pytest.mark.asyncio
async def test_master_key_returns_admin():
    import os
    os.environ["LITELLM_MASTER_KEY"] = "sk-test-master"
    # Reload module to pick up env
    import importlib
    import keycloak_auth
    importlib.reload(keycloak_auth)
    
    user = await keycloak_auth.get_current_user("Bearer sk-test-master")
    assert user.sub == "admin"
    assert user.preferred_username == "admin"
    assert "operators" in user.groups

@pytest.mark.asyncio
async def test_no_auth_header_raises():
    import keycloak_auth
    with pytest.raises(Exception):
        await keycloak_auth.get_current_user(None)

@pytest.mark.asyncio
async def test_invalid_token_raises():
    import keycloak_auth
    with pytest.raises(Exception):
        await keycloak_auth.get_current_user("Bearer invalid-token-xyz")

def test_keycloak_user_dataclass():
    user = KeycloakUser(
        sub="123", email="test@test.com",
        preferred_username="test",
        groups=["operators"],
        realm_access={"roles": ["admin"]}
    )
    assert user.sub == "123"
    assert user.email == "test@test.com"
    assert "operators" in user.groups
