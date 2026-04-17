"""
openfga_authz.py — OpenFGA authorization middleware
Mounted on LiteLLM as custom_auth callback.

Checks every LLM request against OpenFGA:
  1. Is this agent identity active (not suspended/revoked)?
  2. Does this agent have can_use_model relation to the requested model?
  3. Does this agent belong to the calling tenant?

All three must pass. Any failure → 403.

Also exposes:
  POST /authz/grant   — grant a relation tuple
  POST /authz/revoke  — revoke a relation tuple
  POST /authz/check   — arbitrary check (admin only)
  GET  /authz/agent/{agent_name}/models — list models an agent can use
"""

import os, httpx, logging
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

log = logging.getLogger("openfga_authz")

router = APIRouter(prefix="/authz", tags=["Authorization"])

# ── Config ───────────────────────────────────────────────────────────────────

OPENFGA_URL      = os.environ.get("OPENFGA_URL",      "http://openfga:8080")
OPENFGA_STORE_ID = os.environ.get("OPENFGA_STORE_ID", "")
OPENFGA_MODEL_ID = os.environ.get("OPENFGA_AUTH_MODEL_ID", "")
LITELLM_MASTER   = os.environ.get("LITELLM_MASTER_KEY", "")

# Model alias → OpenFGA object name mapping
MODEL_ALIAS_MAP = {
    "ollama/qwen3:30b-a3b":        "model:qwen3-30b-a3b",
    "ollama/qwen2.5-coder:32b":    "model:qwen2.5-coder-32b",
    "ollama/qwen2.5:14b":          "model:qwen2.5-14b",
    "ollama/nomic-embed-text":     "model:nomic-embed-text",
    "ollama/llama3.2-vision:11b":  "model:llama3.2-vision-11b",
    "ollama/llama3.1:8b":          "model:llama3.1-8b",
    "ollama/gemma3:9b":            "model:gemma3-9b",
    "groq/llama3-70b-8192":        "model:groq-llama3-70b",
    "vertex/gemini-2.5-pro":       "model:vertex-gemini-2.5-pro",
    "vertex/gemini-2.5-flash":     "model:vertex-gemini-2.5-flash",
    "claude-3-5-sonnet":           "model:claude-3-5-sonnet",
    "gpt-4o":                      "model:gpt-4o",
}


# ── Core check function ───────────────────────────────────────────────────────

async def fga_check(user: str, relation: str, object_: str) -> bool:
    """
    Perform a single OpenFGA authorization check.
    Returns True if allowed, False if denied or on error.
    """
    if not OPENFGA_STORE_ID:
        log.warning("OPENFGA_STORE_ID not set — skipping authz check (UNSAFE)")
        return True

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(
                f"{OPENFGA_URL}/stores/{OPENFGA_STORE_ID}/check",
                json={
                    "tuple_key": {
                        "user":     user,
                        "relation": relation,
                        "object":   object_,
                    },
                    **({"authorization_model_id": OPENFGA_MODEL_ID}
                       if OPENFGA_MODEL_ID else {}),
                },
            )
            if r.status_code == 200:
                return r.json().get("allowed", False)
            log.error(f"OpenFGA check error {r.status_code}: {r.text}")
            return False
    except Exception as e:
        log.error(f"OpenFGA unreachable: {e}")
        # Fail closed — deny if OpenFGA is down
        return False


async def fga_write(tuples: list, delete: bool = False) -> bool:
    """Write or delete relationship tuples."""
    if not OPENFGA_STORE_ID:
        return True

    key = "deletes" if delete else "writes"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{OPENFGA_URL}/stores/{OPENFGA_STORE_ID}/write",
                json={
                    key: [
                        {"tuple_key": t} for t in tuples
                    ],
                    **({"authorization_model_id": OPENFGA_MODEL_ID}
                       if OPENFGA_MODEL_ID else {}),
                },
            )
            return r.status_code in (200, 204)
    except Exception as e:
        log.error(f"OpenFGA write error: {e}")
        return False


# ── LiteLLM custom_auth callback ─────────────────────────────────────────────

async def custom_auth(api_key: str, request) -> bool:
    """
    LiteLLM custom_auth hook — called before every LLM request.
    LiteLLM passes (api_key, request) — both required.
    Extracts agent identity from key metadata and checks OpenFGA.

    Wire in config.yaml:
      general_settings:
        custom_auth: openfga_authz.custom_auth
    """
    try:
        metadata  = getattr(request, "metadata", {}) or {}
        agent_name = metadata.get("agent_name")
        model      = getattr(request, "model", None) or metadata.get("model")

        # Non-agent requests (tenant users, admin) bypass agent checks
        if not agent_name:
            return True

        agent_obj  = f"agent_identity:{agent_name}"
        model_obj  = MODEL_ALIAS_MAP.get(model, f"model:{model}")
        tenant_id  = metadata.get("tenant_id", "")

        # Check 1: agent can use this model
        model_allowed = await fga_check(
            user=agent_obj,
            relation="can_use_model",
            object_=model_obj,
        )
        if not model_allowed:
            log.warning(f"DENY: {agent_name} → {model} (model not in allowlist)")
            return False

        # Check 2: agent belongs to the calling tenant
        if tenant_id:
            tenant_allowed = await fga_check(
                user=f"tenant:{tenant_id}",
                relation="belongs_to",
                object_=agent_obj,
            )
            if not tenant_allowed:
                log.warning(f"DENY: {agent_name} not in tenant {tenant_id}")
                return False

        log.info(f"ALLOW: {agent_name} → {model}")
        return True

    except Exception as e:
        log.error(f"custom_auth error: {e}")
        return False  # Fail closed


# ── Admin API endpoints ───────────────────────────────────────────────────────

class TupleRequest(BaseModel):
    user:     str
    relation: str
    object:   str


class CheckRequest(BaseModel):
    user:     str
    relation: str
    object:   str


def _require_master(authorization: Optional[str]):
    if not authorization or authorization != f"Bearer {LITELLM_MASTER}":
        raise HTTPException(status_code=401, detail="Master key required")


@router.post("/grant")
async def grant_tuple(
    req: TupleRequest,
    authorization: Optional[str] = Header(None),
):
    """Grant a relationship tuple in OpenFGA."""
    _require_master(authorization)
    success = await fga_write([{
        "user":     req.user,
        "relation": req.relation,
        "object":   req.object,
    }])
    if not success:
        raise HTTPException(status_code=502, detail="OpenFGA write failed")
    return {"status": "granted", "tuple": req.model_dump()}


@router.post("/revoke")
async def revoke_tuple(
    req: TupleRequest,
    authorization: Optional[str] = Header(None),
):
    """Revoke a relationship tuple from OpenFGA."""
    _require_master(authorization)
    success = await fga_write([{
        "user":     req.user,
        "relation": req.relation,
        "object":   req.object,
    }], delete=True)
    if not success:
        raise HTTPException(status_code=502, detail="OpenFGA delete failed")
    return {"status": "revoked", "tuple": req.model_dump()}


@router.post("/check")
async def check_relation(
    req: CheckRequest,
    authorization: Optional[str] = Header(None),
):
    """Perform an arbitrary OpenFGA check (admin only)."""
    _require_master(authorization)
    allowed = await fga_check(req.user, req.relation, req.object)
    return {
        "user":     req.user,
        "relation": req.relation,
        "object":   req.object,
        "allowed":  allowed,
    }


@router.get("/agent/{agent_name}/models")
async def list_agent_models(
    agent_name: str,
    authorization: Optional[str] = Header(None),
):
    """
    List all models an agent has can_use_model relation to.
    Queries OpenFGA list-objects endpoint.
    """
    _require_master(authorization)

    if not OPENFGA_STORE_ID:
        raise HTTPException(status_code=503, detail="OpenFGA not configured")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{OPENFGA_URL}/stores/{OPENFGA_STORE_ID}/list-objects",
                json={
                    "user":      f"agent_identity:{agent_name}",
                    "relation":  "can_use_model",
                    "type":      "model",
                    **({"authorization_model_id": OPENFGA_MODEL_ID}
                       if OPENFGA_MODEL_ID else {}),
                },
            )
            if r.status_code == 200:
                objects = r.json().get("objects", [])
                # Strip "model:" prefix for readability
                models = [o.replace("model:", "") for o in objects]
                return {"agent": agent_name, "allowed_models": models}
            raise HTTPException(status_code=r.status_code, detail=r.text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ── Convenience: grant/revoke model access for an agent ──────────────────────

@router.post("/agent/{agent_name}/grant-model/{model_name}")
async def grant_model_to_agent(
    agent_name: str,
    model_name: str,
    authorization: Optional[str] = Header(None),
):
    """Grant an agent access to a specific model."""
    _require_master(authorization)
    success = await fga_write([{
        "user":     f"model:{model_name}",
        "relation": "can_call_model",
        "object":   f"agent_identity:{agent_name}",
    }])
    if not success:
        raise HTTPException(status_code=502, detail="OpenFGA write failed")
    return {"status": "granted", "agent": agent_name, "model": model_name}


@router.post("/agent/{agent_name}/revoke-model/{model_name}")
async def revoke_model_from_agent(
    agent_name: str,
    model_name: str,
    authorization: Optional[str] = Header(None),
):
    """Revoke an agent's access to a specific model."""
    _require_master(authorization)
    success = await fga_write([{
        "user":     f"model:{model_name}",
        "relation": "can_call_model",
        "object":   f"agent_identity:{agent_name}",
    }], delete=True)
    if not success:
        raise HTTPException(status_code=502, detail="OpenFGA delete failed")
    return {"status": "revoked", "agent": agent_name, "model": model_name}
