"""
Autonomyx Agent Identity System
Entra Agent ID spec — open-source implementation

Principals:
  - Humans: Keycloak OIDC (browser login)
  - Agents: SurrealDB (first-class entity, own lifecycle)
  - Services: Keycloak service accounts (M2M)

Auth flow:
  Human → Keycloak JWT → /agents API → creates agent in SurrealDB + LiteLLM key + OpenFGA tuples
  Agent → LiteLLM Virtual Key → Gateway → OpenFGA check (WHO) → OPA check (CONDITIONS) → Model
"""

from fastapi import FastAPI
from agent_identity import router as identity_router
from agent_discovery import router as discovery_router
from openfga_authz import router as authz_router
from opa_middleware import router as policy_router

app = FastAPI(
    title="Autonomyx Agent Identity",
    description="Entra Agent ID spec — Keycloak + SurrealDB + OpenFGA + OPA",
    version="1.0.0",
)

app.include_router(identity_router)
app.include_router(discovery_router)
app.include_router(authz_router)
app.include_router(policy_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-identity"}
