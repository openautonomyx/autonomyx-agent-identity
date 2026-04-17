"""
opa_middleware.py — OPA conditional policy middleware
OpenFGA: who can access what (relationships)
OPA:     what conditions apply (budget, expiry, DPDP, local-first, TPM)
"""

import os, httpx, logging
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
from litellm.integrations.custom_logger import CustomLogger

log = logging.getLogger("opa_middleware")
router = APIRouter(prefix="/policy", tags=["Policy"])

OPA_URL         = os.environ.get("OPA_URL",          "http://opa:8181")
OPA_POLICY_PATH = os.environ.get("OPA_POLICY_PATH",  "/v1/data/autonomyx/gateway")
LITELLM_MASTER  = os.environ.get("LITELLM_MASTER_KEY", "")

MODEL_METADATA = {
    "ollama/qwen3:30b-a3b":       {"location": "local",  "provider": "ollama",    "region": "local"},
    "ollama/qwen2.5-coder:32b":   {"location": "local",  "provider": "ollama",    "region": "local"},
    "ollama/qwen2.5:14b":         {"location": "local",  "provider": "ollama",    "region": "local"},
    "ollama/nomic-embed-text":    {"location": "local",  "provider": "ollama",    "region": "local"},
    "ollama/llama3.2-vision:11b": {"location": "local",  "provider": "ollama",    "region": "local"},
    "ollama/llama3.1:8b":         {"location": "local",  "provider": "ollama",    "region": "local"},
    "ollama/gemma3:9b":           {"location": "local",  "provider": "ollama",    "region": "local"},
    "groq/llama3-70b-8192":       {"location": "cloud",  "provider": "groq",      "region": "us"},
    "vertex/gemini-2.5-pro":      {"location": "cloud",  "provider": "vertex",    "region": "us-central1"},
    "vertex/gemini-2.5-flash":    {"location": "cloud",  "provider": "vertex",    "region": "us-central1"},
    "claude-3-5-sonnet":          {"location": "cloud",  "provider": "anthropic", "region": "us"},
    "gpt-4o":                     {"location": "cloud",  "provider": "openai",    "region": "us"},
}


async def opa_evaluate(input_data: dict) -> dict:
    """Evaluate OPA policy. Returns allow/deny_reasons. Fails closed on error."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(
                f"{OPA_URL}{OPA_POLICY_PATH}",
                json={"input": input_data},
            )
            if r.status_code == 200:
                result = r.json().get("result", {})
                return {
                    "allow":          result.get("allow", False),
                    "deny_reasons":   list(result.get("deny_reasons", set())),
                    "budget_warning": result.get("budget_warning", False),
                    "metadata":       result.get("decision_metadata", {}),
                }
            log.error(f"OPA {r.status_code}: {r.text}")
            return {"allow": False, "deny_reasons": ["opa_error"], "budget_warning": False}
    except Exception as e:
        log.error(f"OPA unreachable: {e}")
        return {"allow": False, "deny_reasons": ["opa_unreachable"], "budget_warning": False}


def build_opa_input(kwargs: dict, agent_context: dict = None) -> dict:
    """Build OPA input document from LiteLLM request kwargs."""
    model    = kwargs.get("model", "")
    meta     = kwargs.get("litellm_params", {}).get("metadata", {})
    messages = kwargs.get("messages", [])
    prompt   = " ".join(
        m.get("content", "") for m in messages
        if isinstance(m.get("content"), str)
    )
    model_info = MODEL_METADATA.get(model, {
        "location": "unknown", "provider": "unknown", "region": "unknown"
    })
    ctx = agent_context or {}
    now = datetime.now(timezone.utc)
    return {
        "agent": {
            "name":                 meta.get("agent_name", "unknown"),
            "type":                 meta.get("agent_type", "workflow"),
            "tenant_id":            meta.get("tenant_id", ""),
            "budget_limit":         ctx.get("budget_limit", 999.0),
            "spend_this_period":    ctx.get("spend_this_period", 0.0),
            "tpm_limit":            ctx.get("tpm_limit", 999999),
            "tpm_used_last_minute": ctx.get("tpm_used_last_minute", 0),
            "expires_at":           ctx.get("expires_at"),
            "status":               ctx.get("status", "active"),
        },
        "model": {
            "alias":    model,
            "location": model_info["location"],
            "provider": model_info["provider"],
            "region":   model_info["region"],
            "healthy":  True,
        },
        "request": {
            "prompt_length":  len(prompt.split()),
            "contains_pii":   meta.get("contains_pii", False),
            "language":       meta.get("language", "en"),
            "timestamp_utc":  now.isoformat(),
        },
        "system": {
            "local_models_healthy": True,
            "current_hour_utc":     now.hour,
        },
    }


class OPACallback(CustomLogger):
    """LiteLLM custom callback — evaluates OPA before every agent request."""

    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        try:
            agent_name = data.get("metadata", {}).get("agent_name")
            if not agent_name:
                return  # non-agent request — bypass
            opa_input = build_opa_input(data)
            result    = await opa_evaluate(opa_input)
            if result.get("budget_warning"):
                log.warning(f"Budget warning: {agent_name}")
            if not result["allow"]:
                reasons = ", ".join(result["deny_reasons"])
                log.warning(f"OPA DENY: {agent_name} | {reasons}")
                raise Exception(f"Request denied by policy: {reasons}")
            log.info(f"OPA ALLOW: {agent_name} → {opa_input['model']['alias']}")
        except Exception as e:
            if "denied by policy" in str(e):
                raise
            log.error(f"OPA callback error: {e}")
            raise


class PolicyEvalRequest(BaseModel):
    agent_name:           str
    agent_type:           str   = "workflow"
    model:                str
    tenant_id:            str   = ""
    budget_limit:         float = 5.0
    spend_this_period:    float = 0.0
    tpm_limit:            int   = 10000
    tpm_used_last_minute: int   = 0
    contains_pii:         bool  = False
    prompt_length:        int   = 512
    local_models_healthy: bool  = True
    agent_status:         str   = "active"
    expires_at:           Optional[str] = None


@router.post("/evaluate")
async def evaluate_policy(
    req: PolicyEvalRequest,
    authorization: Optional[str] = Header(None),
):
    """Evaluate OPA policy for a given agent+model combo."""
    if not authorization or authorization != f"Bearer {LITELLM_MASTER}":
        raise HTTPException(status_code=401, detail="Master key required")
    model_info = MODEL_METADATA.get(req.model, {
        "location": "unknown", "provider": "unknown", "region": "unknown"
    })
    now = datetime.now(timezone.utc)
    opa_input = {
        "agent": {
            "name": req.agent_name, "type": req.agent_type,
            "tenant_id": req.tenant_id, "budget_limit": req.budget_limit,
            "spend_this_period": req.spend_this_period, "tpm_limit": req.tpm_limit,
            "tpm_used_last_minute": req.tpm_used_last_minute,
            "expires_at": req.expires_at, "status": req.agent_status,
        },
        "model": {"alias": req.model, **model_info, "healthy": True},
        "request": {
            "prompt_length": req.prompt_length, "contains_pii": req.contains_pii,
            "language": "en", "timestamp_utc": now.isoformat(),
        },
        "system": {
            "local_models_healthy": req.local_models_healthy,
            "current_hour_utc": now.hour,
        },
    }
    result = await opa_evaluate(opa_input)
    return {
        "agent": req.agent_name, "model": req.model,
        "allow": result["allow"], "deny_reasons": result["deny_reasons"],
        "budget_warning": result.get("budget_warning", False),
        "opa_input": opa_input,
    }


@router.get("/health")
async def policy_health():
    """Check OPA connectivity."""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{OPA_URL}/health")
            return {"opa": "healthy" if r.status_code == 200 else "unhealthy"}
    except Exception as e:
        return {"opa": "unreachable", "error": str(e)}
