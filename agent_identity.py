"""
agent_identity.py — Autonomyx Agent Identity Layer
FastAPI router mounted on LiteLLM at /agents/*

Implements the Autonomyx Agent Identity Specification v1.0
Reference: references/agent-identity-spec.md

Endpoints:
  POST   /agents/create
  GET    /agents
  GET    /agents/{agent_id}
  POST   /agents/{agent_id}/suspend
  POST   /agents/{agent_id}/reactivate
  POST   /agents/{agent_id}/rotate
  DELETE /agents/{agent_id}
  GET    /agents/{agent_id}/activity
"""

import os, uuid, httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/agents", tags=["Agent Identity"])

# ── Config ──────────────────────────────────────────────────────────────────

LITELLM_URL      = os.environ.get("LITELLM_URL",      "http://localhost:4000")
LITELLM_MASTER   = os.environ.get("LITELLM_MASTER_KEY", "")
SURREAL_URL      = os.environ.get("SURREAL_URL",      "")
SURREAL_NS       = os.environ.get("SURREAL_NS",       "autonomyx")
SURREAL_DB       = os.environ.get("SURREAL_DB",       "gateway")
SURREAL_USER     = os.environ.get("SURREAL_USER",     "")
SURREAL_PASS     = os.environ.get("SURREAL_PASS",     "")

# Default model allowlists per agent name
DEFAULT_MODEL_ALLOWLISTS = {
    "fraud-sentinel":        ["ollama/qwen3:30b-a3b", "groq/llama3-70b-8192"],
    "policy-creator":        ["ollama/qwen3:30b-a3b", "vertex/gemini-2.5-pro"],
    "policy-reviewer":       ["ollama/qwen3:30b-a3b"],
    "code-reviewer":         ["ollama/qwen2.5-coder:32b", "groq/llama3-70b-8192"],
    "feature-gap-analyzer":  ["ollama/qwen3:30b-a3b"],
    "saas-evaluator":        ["ollama/qwen3:30b-a3b"],
    "app-alternatives-finder":["ollama/qwen3:30b-a3b"],
    "saas-standardizer":     ["ollama/qwen3:30b-a3b"],
    "oss-to-saas-analyzer":  ["ollama/qwen3:30b-a3b"],
    "structured-data-parser":["ollama/qwen2.5:14b"],
    "web-scraper":           ["ollama/qwen2.5:14b", "ollama/nomic-embed-text"],
    "gateway-agent":         ["ollama/qwen3:30b-a3b"],
}

DEFAULT_BUDGETS = {
    "workflow":   5.0,
    "skill":      2.0,
    "mcp_tool":   0.10,
    "ephemeral":  1.0,
}

EPHEMERAL_TTL_HOURS = 1


# ── Models ──────────────────────────────────────────────────────────────────

class AgentCreateRequest(BaseModel):
    agent_name:     str                  = Field(..., description="Unique name e.g. fraud-sentinel")
    agent_type:     str                  = Field("workflow", description="workflow|skill|mcp_tool|ephemeral")
    # Administrative roles (per Microsoft Entra Agent ID model)
    sponsor_id:     str                  = Field(..., description="REQUIRED — Business owner accountable for agent lifecycle")
    owner_ids:      List[str]            = Field(default_factory=list, description="Technical admins — manage config and credentials")
    manager_id:     Optional[str]        = Field(None, description="Org hierarchy manager — can request access packages")
    blueprint_id:   Optional[str]        = Field(None, description="Blueprint this agent was created from")
    tenant_id:      str                  = Field(..., description="Keycloak group/tenant")
    allowed_models: Optional[List[str]]  = Field(None, description="Model allowlist — defaults to agent_name preset")
    budget_limit:   Optional[float]      = Field(None, description="Monthly budget USD")
    tpm_limit:      int                  = Field(10000, description="Tokens per minute limit")
    ttl_hours:      Optional[int]        = Field(None, description="Ephemeral TTL — None = permanent")
    metadata:       dict                 = Field(default_factory=dict)


class AgentResponse(BaseModel):
    agent_id:          str
    agent_name:        str
    agent_type:        str
    # Administrative roles
    sponsor_id:        str
    owner_ids:         List[str]
    manager_id:        Optional[str]
    blueprint_id:      Optional[str]
    tenant_id:         str
    allowed_models:    List[str]
    budget_limit:      float
    tpm_limit:         int
    litellm_key_alias: str
    status:            str
    created_at:        str
    last_active_at:    str
    expires_at:        Optional[str]
    metadata:          dict


class AgentCreateResponse(AgentResponse):
    litellm_key: str   # Only returned at creation — never again


# ── Helpers ──────────────────────────────────────────────────────────────────

def _auth_headers():
    return {"Authorization": f"Bearer {LITELLM_MASTER}", "Content-Type": "application/json"}


def _surreal_headers():
    return {
        "surreal-ns": SURREAL_NS,
        "surreal-db": SURREAL_DB,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


async def _surreal_query(query: str, vars: dict = None):
    """Execute a SurrealDB query via JSON-RPC (supports parameterized queries)."""
    if not SURREAL_URL:
        return None
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{SURREAL_URL}/rpc",
            headers=_surreal_headers(),
            auth=(SURREAL_USER, SURREAL_PASS),
            json={
                "id": 1,
                "method": "query",
                "params": [query, vars or {}],
            },
        )
        r.raise_for_status()
        data = r.json()
        return data.get("result", [])


async def _create_litellm_key(
    agent_name: str,
    tenant_id: str,
    allowed_models: List[str],
    budget_limit: float,
    tpm_limit: int,
    expires_at: Optional[datetime],
    agent_id: str,
    sponsor_id: str,
    agent_type: str,
) -> dict:
    """Create a scoped LiteLLM Virtual Key for this agent."""
    key_alias = f"agent:{agent_name}:{tenant_id}"
    payload = {
        "key_alias":       key_alias,
        "models":          allowed_models,
        "max_budget":      budget_limit,
        "budget_duration": "30d",
        "tpm_limit":       tpm_limit,
        "metadata": {
            "agent_id":    agent_id,
            "agent_name":  agent_name,
            "agent_type":  agent_type,
            "tenant_id":   tenant_id,
            "sponsor_id":  sponsor_id,
            "created_by":  "agent_identity_service",
        },
    }
    if expires_at:
        payload["duration"] = f"{int((expires_at - datetime.now(timezone.utc)).total_seconds())}s"

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{LITELLM_URL}/key/generate",
            headers=_auth_headers(),
            json=payload,
        )
        r.raise_for_status()
        return r.json()


async def _delete_litellm_key(key: str):
    """Delete a LiteLLM Virtual Key."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{LITELLM_URL}/key/delete",
            headers=_auth_headers(),
            json={"keys": [key]},
        )
        return r.status_code in (200, 204)


async def _revoke_litellm_key_by_alias(alias: str):
    """Find and delete a LiteLLM key by its alias."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{LITELLM_URL}/key/list", headers=_auth_headers())
        if r.status_code == 200:
            keys = r.json().get("keys", [])
            for k in keys:
                if k.get("key_alias") == alias:
                    await _delete_litellm_key(k["key"])
                    return True
    return False


async def _store_agent(agent: dict):
    """Store agent record in SurrealDB."""
    query = """
        CREATE type::thing('agents', $agent_id) CONTENT {
            agent_id:          $agent_id,
            agent_name:        $agent_name,
            agent_type:        $agent_type,
            sponsor_id:        $sponsor_id,
            owner_ids:         $owner_ids,
            manager_id:        $manager_id,
            blueprint_id:      $blueprint_id,
            tenant_id:         $tenant_id,
            allowed_models:    $allowed_models,
            budget_limit:      $budget_limit,
            tpm_limit:         $tpm_limit,
            litellm_key_alias: $litellm_key_alias,
            status:            'active',
            created_at:        time::now(),
            last_active_at:    time::now(),
            expires_at:        $expires_at,
            metadata:          $metadata
        };
    """
    await _surreal_query(query, agent)


async def _get_agent(agent_id: str) -> Optional[dict]:
    """Fetch agent record from SurrealDB."""
    result = await _surreal_query(
        "SELECT * FROM type::thing('agents', $agent_id);",
        {"agent_id": agent_id}
    )
    if result and result[0].get("result"):
        return result[0]["result"][0]
    return None


async def _update_agent_status(agent_id: str, status: str):
    await _surreal_query(
        "UPDATE type::thing('agents', $agent_id) SET status = $status;",
        {"agent_id": agent_id, "status": status}
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/create", response_model=AgentCreateResponse)
async def create_agent(
    req: AgentCreateRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Provision a new agent identity.
    Returns credentials once — store them securely.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Master key required")

    # Resolve defaults
    agent_id      = str(uuid.uuid4())
    allowed_models = req.allowed_models or DEFAULT_MODEL_ALLOWLISTS.get(req.agent_name, ["ollama/qwen3:30b-a3b"])
    budget_limit  = req.budget_limit or DEFAULT_BUDGETS.get(req.agent_type, 2.0)
    now           = datetime.now(timezone.utc)

    # Compute expiry
    expires_at = None
    if req.agent_type == "ephemeral" or req.ttl_hours:
        hours      = req.ttl_hours or EPHEMERAL_TTL_HOURS
        expires_at = now + timedelta(hours=hours)
    elif req.agent_type == "mcp_tool":
        expires_at = now + timedelta(hours=EPHEMERAL_TTL_HOURS)

    try:
        # Create LiteLLM Virtual Key
        key_data = await _create_litellm_key(
            agent_name=req.agent_name,
            tenant_id=req.tenant_id,
            allowed_models=allowed_models,
            budget_limit=budget_limit,
            tpm_limit=req.tpm_limit,
            expires_at=expires_at,
            agent_id=agent_id,
            sponsor_id=req.sponsor_id,
            agent_type=req.agent_type,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LiteLLM key creation failed: {e}")

    litellm_key   = key_data["key"]
    key_alias     = f"agent:{req.agent_name}:{req.tenant_id}"
    created_at    = now.isoformat()

    # Store in SurrealDB
    await _store_agent({
        "agent_id":          agent_id,
        "agent_name":        req.agent_name,
        "agent_type":        req.agent_type,
        "sponsor_id":        req.sponsor_id,
        "owner_ids":         req.owner_ids or [req.sponsor_id],  # sponsor is default owner
        "manager_id":        req.manager_id,
        "blueprint_id":      req.blueprint_id,
        "tenant_id":         req.tenant_id,
        "allowed_models":    allowed_models,
        "budget_limit":      budget_limit,
        "tpm_limit":         req.tpm_limit,
        "litellm_key_alias": key_alias,
        "expires_at":        expires_at.isoformat() if expires_at else None,
        "metadata":          req.metadata,
    })

    return AgentCreateResponse(
        agent_id=agent_id,
        agent_name=req.agent_name,
        agent_type=req.agent_type,
        sponsor_id=req.sponsor_id,
        owner_ids=req.owner_ids or [req.sponsor_id],
        manager_id=req.manager_id,
        blueprint_id=req.blueprint_id,
        tenant_id=req.tenant_id,
        allowed_models=allowed_models,
        budget_limit=budget_limit,
        tpm_limit=req.tpm_limit,
        litellm_key=litellm_key,        # ONE TIME only
        litellm_key_alias=key_alias,
        status="active",
        created_at=created_at,
        last_active_at=created_at,
        expires_at=expires_at.isoformat() if expires_at else None,
        metadata=req.metadata,
    )


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    tenant_id: Optional[str] = Query(None),
    status:    Optional[str] = Query(None),
    agent_type: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    """List all agent identities with optional filters."""
    filters = []
    vars_   = {}
    if tenant_id:
        filters.append("tenant_id = $tenant_id")
        vars_["tenant_id"] = tenant_id
    if status:
        filters.append("status = $status")
        vars_["status"] = status
    if agent_type:
        filters.append("agent_type = $agent_type")
        vars_["agent_type"] = agent_type

    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    result = await _surreal_query(f"SELECT * FROM agents {where};", vars_)

    agents = []
    if result and result[0].get("result"):
        for a in result[0]["result"]:
            agents.append(AgentResponse(
                agent_id=a["agent_id"],
                agent_name=a["agent_name"],
                agent_type=a["agent_type"],
                sponsor_id=a.get("sponsor_id", ""),
                owner_ids=a.get("owner_ids", []),
                manager_id=a.get("manager_id"),
                blueprint_id=a.get("blueprint_id"),
                tenant_id=a.get("tenant_id", ""),
                allowed_models=a.get("allowed_models", []),
                budget_limit=a.get("budget_limit", 0),
                tpm_limit=a.get("tpm_limit", 0),
                litellm_key_alias=a.get("litellm_key_alias", ""),
                status=a.get("status", "unknown"),
                created_at=str(a.get("created_at", "")),
                last_active_at=str(a.get("last_active_at", "")),
                expires_at=str(a["expires_at"]) if a.get("expires_at") else None,
                metadata=a.get("metadata", {}),
            ))
    return agents


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, authorization: Optional[str] = Header(None)):
    """Get a specific agent identity."""
    agent = await _get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return AgentResponse(**{k: agent.get(k) for k in AgentResponse.model_fields})


@router.post("/{agent_id}/suspend")
async def suspend_agent(agent_id: str, authorization: Optional[str] = Header(None)):
    """
    Suspend an agent — revoke its LiteLLM key, preserve identity.
    Can be reactivated later with a new key.
    """
    agent = await _get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    if agent["status"] != "active":
        raise HTTPException(status_code=409, detail=f"Agent is {agent['status']}, not active")

    await _revoke_litellm_key_by_alias(agent["litellm_key_alias"])

    await _update_agent_status(agent_id, "suspended")
    return {"agent_id": agent_id, "status": "suspended", "message": "Agent suspended. Use /reactivate to restore."}


@router.post("/{agent_id}/reactivate", response_model=AgentCreateResponse)
async def reactivate_agent(agent_id: str, authorization: Optional[str] = Header(None)):
    """
    Reactivate a suspended agent — issues a new LiteLLM key.
    Same agent_id, new credentials.
    """
    agent = await _get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    if agent["status"] == "revoked":
        raise HTTPException(status_code=409, detail="Revoked agents cannot be reactivated")
    if agent["status"] == "active":
        raise HTTPException(status_code=409, detail="Agent is already active")

    key_data = await _create_litellm_key(
        agent_name=agent["agent_name"],
        tenant_id=agent["tenant_id"],
        allowed_models=agent["allowed_models"],
        budget_limit=agent["budget_limit"],
        tpm_limit=agent["tpm_limit"],
        expires_at=None,
        agent_id=agent_id,
        sponsor_id=agent["sponsor_id"],
        agent_type=agent["agent_type"],
    )

    await _update_agent_status(agent_id, "active")

    return AgentCreateResponse(
        **{k: agent.get(k) for k in AgentResponse.model_fields},
        litellm_key=key_data["key"],
    )


@router.post("/{agent_id}/rotate", response_model=AgentCreateResponse)
async def rotate_agent_key(agent_id: str, authorization: Optional[str] = Header(None)):
    """
    Rotate agent credentials — zero downtime.
    New key is issued before old key is deleted.
    """
    agent = await _get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    if agent["status"] != "active":
        raise HTTPException(status_code=409, detail=f"Cannot rotate key for {agent['status']} agent")

    # Issue new key first (zero downtime)
    new_key_data = await _create_litellm_key(
        agent_name=agent["agent_name"],
        tenant_id=agent["tenant_id"],
        allowed_models=agent["allowed_models"],
        budget_limit=agent["budget_limit"],
        tpm_limit=agent["tpm_limit"],
        expires_at=None,
        agent_id=agent_id,
        sponsor_id=agent["sponsor_id"],
        agent_type=agent["agent_type"],
    )

    await _revoke_litellm_key_by_alias(agent["litellm_key_alias"])

    return AgentCreateResponse(
        **{k: agent.get(k) for k in AgentResponse.model_fields},
        litellm_key=new_key_data["key"],
    )


@router.delete("/{agent_id}")
async def revoke_agent(agent_id: str, authorization: Optional[str] = Header(None)):
    """
    Permanently revoke an agent identity.
    Deletes LiteLLM key. SurrealDB record retained for audit.
    Cannot be undone.
    """
    agent = await _get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    if agent["status"] == "revoked":
        raise HTTPException(status_code=409, detail="Agent already revoked")

    await _revoke_litellm_key_by_alias(agent["litellm_key_alias"])

    # Mark as revoked — record retained for audit
    await _update_agent_status(agent_id, "revoked")

    return {
        "agent_id": agent_id,
        "status": "revoked",
        "message": "Agent permanently revoked. Identity record retained for audit.",
    }


@router.get("/{agent_id}/activity")
async def get_agent_activity(
    agent_id: str,
    limit: int = Query(50, ge=1, le=500),
    authorization: Optional[str] = Header(None),
):
    """
    Get recent activity for an agent from SurrealDB usage log.
    """
    result = await _surreal_query(
        """
        SELECT created_at, model, input_tokens, output_tokens, status
        FROM agent_calls
        WHERE agent_id = $agent_id
        ORDER BY created_at DESC
        LIMIT $limit;
        """,
        {"agent_id": agent_id, "limit": limit}
    )

    calls = []
    if result and result[0].get("result"):
        calls = result[0]["result"]

    return {
        "agent_id": agent_id,
        "total_calls": len(calls),
        "calls": calls,
    }
