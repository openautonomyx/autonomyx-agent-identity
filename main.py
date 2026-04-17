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

from contextlib import asynccontextmanager
from fastapi import FastAPI
from infisical_secrets import load_secrets

load_secrets()

from agent_identity import router as identity_router
from agent_discovery import router as discovery_router
from openfga_authz import router as authz_router
from opa_middleware import router as policy_router
from audit import router as audit_router
from blueprints import router as blueprints_router
from bulk_ops import router as bulk_router
from webhooks import router as webhooks_router
from expiry_worker import check_and_expire
import asyncio


async def _expiry_loop():
    while True:
        try:
            await check_and_expire()
        except Exception:
            pass
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_expiry_loop())
    yield
    task.cancel()


app = FastAPI(
    title="Autonomyx Agent Identity",
    description="Entra Agent ID spec — Keycloak + SurrealDB + OpenFGA + OPA",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(identity_router)
app.include_router(discovery_router)
app.include_router(authz_router)
app.include_router(policy_router)
app.include_router(audit_router)
app.include_router(blueprints_router)
app.include_router(bulk_router)
app.include_router(webhooks_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-identity"}
