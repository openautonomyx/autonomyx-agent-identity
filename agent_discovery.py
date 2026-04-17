"""
agent_discovery.py — Agent Auth Protocol discovery endpoint
Exposes /.well-known/agent-configuration so other agents and platforms
can discover what this gateway offers and how to interact with it.

Reference: https://agentauthprotocol.com
Reference: https://better-auth.com/docs/plugins/agent-auth
"""

import os
from fastapi import APIRouter
from typing import Optional

router = APIRouter(tags=["Discovery"])

GATEWAY_URL    = os.environ.get("GATEWAY_URL",    "https://llm.openautonomyx.com")
GATEWAY_NAME   = os.environ.get("GATEWAY_NAME",   "Autonomyx Model Gateway")
GATEWAY_ORG    = os.environ.get("GATEWAY_ORG",    "OPENAUTONOMYX (OPC) PRIVATE LIMITED")
FLOWS_URL      = os.environ.get("FLOWS_URL",       "https://flows.openautonomyx.com")
MCP_URL        = os.environ.get("MCP_URL",         "https://mcp.openautonomyx.com")


@router.get("/.well-known/agent-configuration")
async def agent_configuration():
    """
    Agent Auth Protocol discovery document.
    Allows external agents and platforms to discover:
      - What this gateway is
      - What capabilities it exposes
      - How to register and authenticate
      - Which modes are supported (autonomous/delegated)
    """
    return {
        # ── Provider identity ────────────────────────────────────────────────
        "issuer":               GATEWAY_URL,
        "provider_name":        GATEWAY_NAME,
        "provider_description": (
            "FullStack AI infrastructure for India. Self-hosted LLM gateway with "
            "local models, intelligent routing, metered billing, and 22 Indian languages. "
            "OpenAI-compatible API."
        ),
        "organization":         GATEWAY_ORG,
        "homepage":             "https://openautonomyx.com",
        "contact":              "chinmay@openautonomyx.com",

        # ── Supported agent modes ─────────────────────────────────────────────
        "modes": ["autonomous", "delegated"],

        # ── Authentication ────────────────────────────────────────────────────
        "authn_methods": [
            {
                "type":        "bearer_token",
                "description": "LiteLLM Virtual Key — scoped per agent",
                "header":      "Authorization: Bearer sk-...",
            }
        ],

        # ── Agent registration ────────────────────────────────────────────────
        "registration": {
            "endpoint":    f"{GATEWAY_URL}/agents/create",
            "method":      "POST",
            "description": "Create a new agent identity with scoped model access",
            "requires":    ["agent_name", "sponsor_id", "tenant_id"],
            "docs":        "https://github.com/openautonomyx/autonomyx-model-gateway/blob/main/docs/quickstart.md",
        },

        # ── Capabilities ──────────────────────────────────────────────────────
        "capabilities": [
            {
                "name":        "llm_inference",
                "description": "OpenAI-compatible LLM inference with local and cloud models",
                "endpoint":    f"{GATEWAY_URL}/v1/chat/completions",
                "method":      "POST",
                "models": [
                    "ollama/qwen3:30b-a3b",
                    "ollama/qwen2.5-coder:32b",
                    "ollama/qwen2.5:14b",
                    "groq/llama3-70b-8192",
                    "vertex/gemini-2.5-pro",
                ],
                "openai_compatible": True,
            },
            {
                "name":        "model_recommendation",
                "description": "Get ranked model recommendations for a given task",
                "endpoint":    f"{GATEWAY_URL}/recommend",
                "method":      "POST",
                "input": {
                    "prompt":         "string — task description",
                    "require_local":  "bool — restrict to local models only",
                    "top_n":          "int — number of recommendations",
                },
            },
            {
                "name":        "fraud_detection",
                "description": "7-pattern fraud detection with ALLOW/WARN/BLOCK verdict. DPDP compliant.",
                "endpoint":    f"{FLOWS_URL}/api/v1/run/fraud-sentinel",
                "method":      "POST",
                "agent":       "fraud-sentinel",
            },
            {
                "name":        "policy_creation",
                "description": "Generate Privacy Policy, Terms of Service, Cookie Policy. DPDP 2023/GDPR/CCPA aware.",
                "endpoint":    f"{FLOWS_URL}/api/v1/run/policy-creator",
                "method":      "POST",
                "agent":       "policy-creator",
            },
            {
                "name":        "policy_review",
                "description": "Analyse vendor policies across 5 domains: privacy, AI training, security, carbon, governance.",
                "endpoint":    f"{FLOWS_URL}/api/v1/run/policy-reviewer",
                "method":      "POST",
                "agent":       "policy-reviewer",
            },
            {
                "name":        "code_review",
                "description": "Bug detection, security analysis, style violations, improvement suggestions.",
                "endpoint":    f"{FLOWS_URL}/api/v1/run/code-reviewer",
                "method":      "POST",
                "agent":       "code-reviewer",
            },
            {
                "name":        "feature_gap_analysis",
                "description": "Compare enterprise software across 8 dimensions. Scored matrix output.",
                "endpoint":    f"{FLOWS_URL}/api/v1/run/feature-gap-analyzer",
                "method":      "POST",
                "agent":       "feature-gap-analyzer",
            },
            {
                "name":        "saas_evaluation",
                "description": "Multi-persona SaaS evaluation (CTO/CISO/Procurement). 8-dimension scores.",
                "endpoint":    f"{FLOWS_URL}/api/v1/run/saas-evaluator",
                "method":      "POST",
                "agent":       "saas-evaluator",
            },
            {
                "name":        "web_scraping",
                "description": "Crawl URLs, extract structured data, embed to vector store for RAG.",
                "endpoint":    f"{FLOWS_URL}/api/v1/run/web-scraper",
                "method":      "POST",
                "agent":       "web-scraper",
            },
            {
                "name":        "structured_data_parsing",
                "description": "Parse JSON, CSV, XML, YAML, Markdown tables. Auto-detect format.",
                "endpoint":    f"{FLOWS_URL}/api/v1/run/structured-data-parser",
                "method":      "POST",
                "agent":       "structured-data-parser",
            },
            {
                "name":        "oss_to_saas_analysis",
                "description": "Score OSS projects across 5 commercial archetypes. 90-day action plan.",
                "endpoint":    f"{FLOWS_URL}/api/v1/run/oss-to-saas-analyzer",
                "method":      "POST",
                "agent":       "oss-to-saas-analyzer",
            },
            {
                "name":        "translation",
                "description": "Translate text across 22 Indian scheduled languages.",
                "endpoint":    f"{GATEWAY_URL}/translate",
                "method":      "POST",
                "languages":   [
                    "hi", "ta", "te", "bn", "kn", "ml", "gu", "mr",
                    "pa", "ur", "or", "as", "mai", "sat", "ks", "kok",
                    "sd", "doi", "mni", "brx", "sa", "ne"
                ],
            },
            {
                "name":        "feedback",
                "description": "Submit human feedback on LLM responses. Routed to Langfuse.",
                "endpoint":    f"{GATEWAY_URL}/feedback",
                "method":      "POST",
            },
            {
                "name":        "mcp_tools",
                "description": "MCP server exposing all gateway capabilities as typed tools.",
                "endpoint":    MCP_URL,
                "protocol":    "mcp",
            },
        ],

        # ── Authorization model ───────────────────────────────────────────────
        "authorization": {
            "model":       "relationship-based + conditional",
            "rbac":        "OpenFGA — agent identity, model access, tenant ownership",
            "conditions":  "OPA — budget, DPDP, local-first, expiry, TPM",
            "compliance":  ["DPDP Act 2023", "GDPR", "CCPA"],
        },

        # ── Infrastructure ────────────────────────────────────────────────────
        "infrastructure": {
            "local_models":  True,
            "cloud_fallback": True,
            "self_hosted":   True,
            "india_region":  True,
            "data_residency": "VPS in EU (OVH) — private node option available for India residency",
        },

        # ── Agent lifecycle endpoints ─────────────────────────────────────────
        "endpoints": {
            "register":    f"{GATEWAY_URL}/agents/create",
            "list_agents": f"{GATEWAY_URL}/agents",
            "suspend":     f"{GATEWAY_URL}/agents/{{agent_id}}/suspend",
            "rotate_key":  f"{GATEWAY_URL}/agents/{{agent_id}}/rotate",
            "revoke":      f"{GATEWAY_URL}/agents/{{agent_id}}",
            "check_authz": f"{GATEWAY_URL}/authz/check",
            "eval_policy": f"{GATEWAY_URL}/policy/evaluate",
            "execute":     f"{GATEWAY_URL}/v1/chat/completions",
            "models":      f"{GATEWAY_URL}/v1/models",
            "health":      f"{GATEWAY_URL}/health",
            "discovery":   f"{GATEWAY_URL}/.well-known/agent-configuration",
        },

        # ── Spec version ──────────────────────────────────────────────────────
        "agent_auth_protocol_version": "0.1",
        "schema_version": "1.0",
    }


@router.get("/.well-known/agent-configuration.json")
async def agent_configuration_json():
    """Alias — some clients request .json extension."""
    return await agent_configuration()
