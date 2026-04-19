"""Autonomyx Agent Identity Plane API."""

from contextlib import asynccontextmanager
import asyncio
import logging

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from infisical_secrets import load_secrets
from settings import get_settings
from observability import RequestContextMiddleware, configure_logging

load_secrets()

from agent_identity import router as identity_router
from agent_discovery import router as discovery_router
from openfga_authz import router as authz_router
from opa_middleware import router as policy_router
from audit import router as audit_router
from blueprints import router as blueprints_router
from bulk_ops import router as bulk_router
from webhooks import router as webhooks_router
from scim import router as scim_router
from expiry_worker import check_and_expire

settings = get_settings()
configure_logging(settings.log_level)
log = logging.getLogger("main")


async def _expiry_loop():
    while True:
        try:
            await check_and_expire()
        except Exception as exc:
            log.exception("expiry loop failed: %s", exc)
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_expiry_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


import contextlib
app = FastAPI(
    title=settings.app_name,
    description="Entra Agent ID spec — Keycloak + SurrealDB + OpenFGA + OPA",
    version=settings.app_version,
    lifespan=lifespan,
)
app.add_middleware(RequestContextMiddleware)

if settings.cors_allow_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id", "Idempotency-Key"],
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled exception at %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Unexpected server error"}},
    )


app.include_router(identity_router)
app.include_router(discovery_router)
app.include_router(authz_router)
app.include_router(policy_router)
app.include_router(audit_router)
app.include_router(blueprints_router)
app.include_router(bulk_router)
app.include_router(webhooks_router)
app.include_router(scim_router)


@app.get("/health/live")
async def health_live():
    return {"status": "ok", "service": "agent-identity"}


@app.get("/health/ready")
async def health_ready():
    checks = {"surreal": "unknown", "opa": "unknown", "openfga": "unknown"}

    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            if settings.surreal_url:
                r = await client.get(f"{settings.surreal_url}/health")
                checks["surreal"] = "ok" if r.status_code < 500 else "error"
        except Exception:
            checks["surreal"] = "error"

        try:
            r = await client.get(f"{settings.opa_url}/health")
            checks["opa"] = "ok" if r.status_code == 200 else "error"
        except Exception:
            checks["opa"] = "error"

        try:
            r = await client.get(f"{settings.openfga_url}/healthz")
            checks["openfga"] = "ok" if r.status_code < 500 else "error"
        except Exception:
            checks["openfga"] = "error"

    ready = all(v in {"ok", "unknown"} for v in checks.values())
    return JSONResponse(status_code=200 if ready else 503, content={"status": "ok" if ready else "degraded", "checks": checks})


@app.get("/health")
async def health():
    return await health_live()
