"""
agent_bootstrap.py — Pre-provision all Autonomyx workflow agents

Run once after first deploy:
  docker exec autonomyx-litellm python agent_bootstrap.py

Idempotent — skips agents that already exist in LiteLLM.
"""

import os, asyncio, httpx

LITELLM_URL    = os.environ.get("LITELLM_URL", "http://localhost:4000")
LITELLM_MASTER = os.environ.get("LITELLM_MASTER_KEY", "")
SPONSOR_ID     = os.environ.get("BOOTSTRAP_SPONSOR_ID", "admin@openautonomyx.com")
TENANT_ID      = os.environ.get("BOOTSTRAP_TENANT_ID", "autonomyx-internal")

AGENTS = [
    {"name": "fraud-sentinel",          "models": ["ollama/qwen3:30b-a3b", "groq/llama3-70b-8192"],        "budget": 2.0,  "tpm": 10000},
    {"name": "policy-creator",          "models": ["ollama/qwen3:30b-a3b", "vertex/gemini-2.5-pro"],        "budget": 5.0,  "tpm": 10000},
    {"name": "policy-reviewer",         "models": ["ollama/qwen3:30b-a3b"],                                 "budget": 2.0,  "tpm": 10000},
    {"name": "code-reviewer",           "models": ["ollama/qwen2.5-coder:32b", "groq/llama3-70b-8192"],     "budget": 3.0,  "tpm": 20000},
    {"name": "feature-gap-analyzer",    "models": ["ollama/qwen3:30b-a3b"],                                 "budget": 3.0,  "tpm": 10000},
    {"name": "saas-evaluator",          "models": ["ollama/qwen3:30b-a3b"],                                 "budget": 3.0,  "tpm": 10000},
    {"name": "app-alternatives-finder", "models": ["ollama/qwen3:30b-a3b"],                                 "budget": 2.0,  "tpm": 10000},
    {"name": "saas-standardizer",       "models": ["ollama/qwen3:30b-a3b"],                                 "budget": 2.0,  "tpm": 10000},
    {"name": "oss-to-saas-analyzer",    "models": ["ollama/qwen3:30b-a3b"],                                 "budget": 2.0,  "tpm": 10000},
    {"name": "structured-data-parser",  "models": ["ollama/qwen2.5:14b"],                                   "budget": 1.0,  "tpm": 20000},
    {"name": "web-scraper",             "models": ["ollama/qwen2.5:14b", "ollama/nomic-embed-text"],        "budget": 2.0,  "tpm": 20000},
    {"name": "gateway-agent",           "models": ["ollama/qwen3:30b-a3b"],                                 "budget": 5.0,  "tpm": 50000},
]


async def get_existing_keys():
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{LITELLM_URL}/key/list",
            headers={"Authorization": f"Bearer {LITELLM_MASTER}"},
        )
        if r.status_code == 200:
            return {k.get("key_alias"): k for k in r.json().get("keys", [])}
    return {}


async def create_agent_key(agent: dict, existing: dict):
    alias = f"agent:{agent['name']}:{TENANT_ID}"
    if alias in existing:
        print(f"  ✓ {agent['name']} — already exists, skipping")
        return None

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{LITELLM_URL}/key/generate",
            headers={"Authorization": f"Bearer {LITELLM_MASTER}", "Content-Type": "application/json"},
            json={
                "key_alias":       alias,
                "models":          agent["models"],
                "max_budget":      agent["budget"],
                "budget_duration": "30d",
                "tpm_limit":       agent["tpm"],
                "metadata": {
                    "agent_name":  agent["name"],
                    "agent_type":  "workflow",
                    "tenant_id":   TENANT_ID,
                    "sponsor_id":  SPONSOR_ID,
                    "created_by":  "agent_bootstrap",
                },
            },
        )
        if r.status_code == 200:
            key = r.json()["key"]
            print(f"  ✓ {agent['name']} — created ({alias})")
            print(f"    Key: {key[:20]}...{key[-4:]} [store securely]")
            return {"name": agent["name"], "alias": alias, "key": key}
        else:
            print(f"  ✗ {agent['name']} — FAILED: {r.text}")
            return None


async def bootstrap():
    if not LITELLM_MASTER:
        print("ERROR: LITELLM_MASTER_KEY not set")
        return

    print(f"\n{'='*60}")
    print(" Autonomyx Agent Identity Bootstrap")
    print(f"{'='*60}")
    print(f" Tenant:  {TENANT_ID}")
    print(f" Sponsor: {SPONSOR_ID}")
    print(f" Agents:  {len(AGENTS)}")
    print(f"{'='*60}\n")

    existing = await get_existing_keys()
    print(f"Existing keys: {len(existing)}\n")

    created = []
    for agent in AGENTS:
        result = await create_agent_key(agent, existing)
        if result:
            created.append(result)

    print(f"\n{'='*60}")
    print(f" Bootstrap complete — {len(created)} agents created")
    if created:
        print("\n IMPORTANT: Save these credentials now.")
        print(" They will not be shown again.\n")
        for a in created:
            print(f"  {a['name']}: {a['key']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(bootstrap())
