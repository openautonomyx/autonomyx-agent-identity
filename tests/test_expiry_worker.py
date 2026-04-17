"""tests/test_expiry_worker.py — Unit tests for expiry_worker.py"""
import pytest
import respx
import httpx
import os
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta

os.environ.setdefault("SURREAL_URL", "http://surrealdb:8000")
os.environ.setdefault("SURREAL_NS", "autonomyx")
os.environ.setdefault("SURREAL_DB", "agents")
os.environ.setdefault("SURREAL_USER", "root")
os.environ.setdefault("SURREAL_PASS", "root")
os.environ.setdefault("LITELLM_MASTER_KEY", "test-master-key")

import expiry_worker

SURREAL_URL = "http://surrealdb:8000"

EXPIRED_AGENT = {
    "agent_id": "agent-expired",
    "agent_name": "temp-agent",
    "status": "active",
    "tenant_id": "tenant-acme",
    "expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
}


# ── check_and_expire ─────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
@patch("expiry_worker.log_event", new_callable=AsyncMock)
async def test_expire_finds_and_updates(mock_log):
    respx.post(f"{SURREAL_URL}/sql").mock(side_effect=[
        httpx.Response(200, json=[{"result": [EXPIRED_AGENT], "status": "OK"}]),
        httpx.Response(200, json=[{"result": [], "status": "OK"}]),
    ])
    count = await expiry_worker.check_and_expire()
    assert count == 1
    mock_log.assert_called_once()
    call_args = mock_log.call_args
    assert call_args[0][0] == "agent.expired"
    assert call_args[0][1] == "agent-expired"


@pytest.mark.asyncio
@respx.mock
@patch("expiry_worker.log_event", new_callable=AsyncMock)
async def test_expire_no_expired_agents(mock_log):
    respx.post(f"{SURREAL_URL}/sql").mock(
        return_value=httpx.Response(200, json=[{"result": [], "status": "OK"}])
    )
    count = await expiry_worker.check_and_expire()
    assert count == 0
    mock_log.assert_not_called()


@pytest.mark.asyncio
@respx.mock
@patch("expiry_worker.log_event", new_callable=AsyncMock)
async def test_expire_multiple_agents(mock_log):
    agents = [
        {**EXPIRED_AGENT, "agent_id": "a1", "agent_name": "temp-1"},
        {**EXPIRED_AGENT, "agent_id": "a2", "agent_name": "temp-2"},
    ]
    respx.post(f"{SURREAL_URL}/sql").mock(side_effect=[
        httpx.Response(200, json=[{"result": agents, "status": "OK"}]),
        httpx.Response(200, json=[{"result": [], "status": "OK"}]),
        httpx.Response(200, json=[{"result": [], "status": "OK"}]),
    ])
    count = await expiry_worker.check_and_expire()
    assert count == 2
    assert mock_log.call_count == 2
