"""tests/test_agent_bootstrap.py
Full coverage for agent_bootstrap.py.
Mocks all httpx HTTP calls with respx — no real LiteLLM needed.
"""
import pytest
import asyncio
import httpx
import respx
from unittest.mock import patch
import os

# Set required env vars before import
os.environ.setdefault("LITELLM_MASTER_KEY", "test-master-key")
os.environ.setdefault("LITELLM_URL", "http://litellm:4000")
os.environ.setdefault("BOOTSTRAP_SPONSOR_ID", "admin@openautonomyx.com")
os.environ.setdefault("BOOTSTRAP_TENANT_ID", "autonomyx-internal")

import sys, os as _os
sys.path.insert(0, str(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
import agent_bootstrap as ab


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


FAKE_KEY = "sk-test-" + "x" * 40


# ── get_existing_keys ─────────────────────────────────────────────────────────

@respx.mock
def test_get_existing_keys_success():
    """Returns dict keyed by key_alias."""
    respx.get(f"{ab.LITELLM_URL}/key/list").mock(
        return_value=httpx.Response(200, json={
            "keys": [
                {"key_alias": "agent:fraud-sentinel:autonomyx-internal", "key": FAKE_KEY},
                {"key_alias": "agent:code-reviewer:autonomyx-internal",  "key": FAKE_KEY},
            ]
        })
    )
    result = run(ab.get_existing_keys())
    assert "agent:fraud-sentinel:autonomyx-internal" in result
    assert "agent:code-reviewer:autonomyx-internal" in result
    assert len(result) == 2


@respx.mock
def test_get_existing_keys_empty():
    """Returns empty dict when no keys exist."""
    respx.get(f"{ab.LITELLM_URL}/key/list").mock(
        return_value=httpx.Response(200, json={"keys": []})
    )
    result = run(ab.get_existing_keys())
    assert result == {}


@respx.mock
def test_get_existing_keys_api_error():
    """Returns empty dict on non-200 response — does not raise."""
    respx.get(f"{ab.LITELLM_URL}/key/list").mock(
        return_value=httpx.Response(401, json={"error": "unauthorized"})
    )
    result = run(ab.get_existing_keys())
    assert result == {}


@respx.mock
def test_get_existing_keys_missing_alias():
    """Handles keys with no key_alias field (key=None in dict)."""
    respx.get(f"{ab.LITELLM_URL}/key/list").mock(
        return_value=httpx.Response(200, json={
            "keys": [{"key": FAKE_KEY}]  # no key_alias
        })
    )
    result = run(ab.get_existing_keys())
    assert None in result  # key with no alias is stored under None


# ── create_agent_key ──────────────────────────────────────────────────────────

@respx.mock
def test_create_agent_key_new(capsys):
    """Creates a new key when alias not in existing."""
    respx.post(f"{ab.LITELLM_URL}/key/generate").mock(
        return_value=httpx.Response(200, json={"key": FAKE_KEY})
    )
    agent = ab.AGENTS[0]  # fraud-sentinel
    result = run(ab.create_agent_key(agent, existing={}))
    assert result is not None
    assert result["name"] == agent["name"]
    assert result["key"] == FAKE_KEY
    out = capsys.readouterr().out
    assert "created" in out


@respx.mock
def test_create_agent_key_already_exists(capsys):
    """Skips creation when alias already exists."""
    agent = ab.AGENTS[0]
    alias = f"agent:{agent['name']}:{ab.TENANT_ID}"
    existing = {alias: {"key": FAKE_KEY, "key_alias": alias}}

    result = run(ab.create_agent_key(agent, existing=existing))

    assert result is None
    out = capsys.readouterr().out
    assert "skipping" in out


@respx.mock
def test_create_agent_key_api_failure(capsys):
    """Returns None and prints error on non-200 response."""
    respx.post(f"{ab.LITELLM_URL}/key/generate").mock(
        return_value=httpx.Response(500, json={"error": "internal server error"})
    )
    agent = ab.AGENTS[0]
    result = run(ab.create_agent_key(agent, existing={}))
    assert result is None
    out = capsys.readouterr().out
    assert "FAILED" in out


@respx.mock
def test_create_agent_key_correct_payload():
    """Verifies the payload sent to LiteLLM is correct."""
    captured = {}

    def capture(request, route):
        import json as _json
        captured["body"] = _json.loads(request.content)
        return httpx.Response(200, json={"key": FAKE_KEY})

    respx.post(f"{ab.LITELLM_URL}/key/generate").mock(side_effect=capture)

    agent = {"name": "test-agent", "models": ["ollama/qwen3:30b-a3b"], "budget": 1.5, "tpm": 5000}
    run(ab.create_agent_key(agent, existing={}))

    body = captured["body"]
    assert body["max_budget"] == 1.5
    assert body["tpm_limit"] == 5000
    assert "ollama/qwen3:30b-a3b" in body["models"]
    assert body["budget_duration"] == "30d"
    assert body["metadata"]["agent_type"] == "workflow"
    assert body["metadata"]["tenant_id"] == ab.TENANT_ID
    assert body["metadata"]["sponsor_id"] == ab.SPONSOR_ID


# ── bootstrap (full flow) ─────────────────────────────────────────────────────

@respx.mock
def test_bootstrap_full_flow(capsys):
    """Full bootstrap: gets existing keys then creates all agents."""
    # No existing keys
    respx.get(f"{ab.LITELLM_URL}/key/list").mock(
        return_value=httpx.Response(200, json={"keys": []})
    )
    # All creates succeed
    respx.post(f"{ab.LITELLM_URL}/key/generate").mock(
        return_value=httpx.Response(200, json={"key": FAKE_KEY})
    )
    run(ab.bootstrap())
    out = capsys.readouterr().out
    assert "Bootstrap complete" in out
    assert f"{len(ab.AGENTS)} agents created" in out


@respx.mock
def test_bootstrap_all_existing(capsys):
    """Bootstrap skips all agents when they all already exist."""
    # All agents already exist
    existing_keys = []
    for agent in ab.AGENTS:
        alias = f"agent:{agent['name']}:{ab.TENANT_ID}"
        existing_keys.append({"key_alias": alias, "key": FAKE_KEY})

    respx.get(f"{ab.LITELLM_URL}/key/list").mock(
        return_value=httpx.Response(200, json={"keys": existing_keys})
    )
    run(ab.bootstrap())
    out = capsys.readouterr().out
    assert "0 agents created" in out


@respx.mock
def test_bootstrap_no_master_key(capsys):
    """Bootstrap exits early with error when LITELLM_MASTER_KEY not set."""
    original = ab.LITELLM_MASTER
    ab.LITELLM_MASTER = ""
    try:
        run(ab.bootstrap())
        out = capsys.readouterr().out
        assert "ERROR" in out
    finally:
        ab.LITELLM_MASTER = original


@respx.mock
def test_bootstrap_partial_existing(capsys):
    """Bootstrap creates only missing agents when some already exist."""
    # First 6 agents already exist
    existing_keys = []
    for agent in ab.AGENTS[:6]:
        alias = f"agent:{agent['name']}:{ab.TENANT_ID}"
        existing_keys.append({"key_alias": alias, "key": FAKE_KEY})

    respx.get(f"{ab.LITELLM_URL}/key/list").mock(
        return_value=httpx.Response(200, json={"keys": existing_keys})
    )
    respx.post(f"{ab.LITELLM_URL}/key/generate").mock(
        return_value=httpx.Response(200, json={"key": FAKE_KEY})
    )
    run(ab.bootstrap())
    out = capsys.readouterr().out
    expected_created = len(ab.AGENTS) - 6
    assert f"{expected_created} agents created" in out


# ── AGENTS list integrity ─────────────────────────────────────────────────────

def test_agents_list_not_empty():
    assert len(ab.AGENTS) > 0


def test_agents_all_have_required_fields():
    for agent in ab.AGENTS:
        assert "name" in agent, f"Agent missing 'name': {agent}"
        assert "models" in agent, f"Agent '{agent['name']}' missing 'models'"
        assert "budget" in agent, f"Agent '{agent['name']}' missing 'budget'"
        assert "tpm" in agent, f"Agent '{agent['name']}' missing 'tpm'"
        assert len(agent["models"]) > 0, f"Agent '{agent['name']}' has empty models list"
        assert agent["budget"] > 0, f"Agent '{agent['name']}' has non-positive budget"
        assert agent["tpm"] > 0, f"Agent '{agent['name']}' has non-positive tpm"


def test_agents_unique_names():
    names = [a["name"] for a in ab.AGENTS]
    assert len(names) == len(set(names)), f"Duplicate agent names: {[n for n in names if names.count(n) > 1]}"
