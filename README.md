# Autonomyx Agent Identity Plane

A FastAPI-based **Agent Identity Plane** that provides lifecycle, discovery, policy, authorization, audit, webhooks, and SCIM-style provisioning for AI agents.

## What this project is

This service manages machine identities for agents and enforces runtime access constraints using:
- **Keycloak** for human/service authentication.
- **SurrealDB** for agent identity state.
- **OpenFGA** for relationship authorization (who can use what).
- **OPA** for conditional policy evaluation (budget, expiry, model constraints).

## Core capabilities

- Agent lifecycle APIs (`/agents`) for create/list/get/suspend/reactivate/rotate/revoke.
- Agent discovery (`/.well-known/agent-configuration`).
- OpenFGA tuple administration and checks (`/authz/*`).
- OPA policy evaluation endpoint (`/policy/evaluate`).
- Audit event endpoints (`/audit/*`).
- Webhook registration + event delivery (`/webhooks/*`).
- SCIM-style endpoints (`/scim/v2/*`) for users/groups.
- Background expiry worker for TTL-based identities.

## Production-ready vs experimental

### Production-ready now
- Typed startup config validation with prod fail-fast checks.
- Liveness/readiness endpoints (`/health/live`, `/health/ready`).
- Request correlation headers and structured logging baseline.
- Webhook HMAC signature headers for registered secrets.
- Durable production compose sample (`deploy/docker-compose.prod.yml`).
- CI workflow with lint/tests/security checks.

### Still experimental / roadmap
- End-to-end transactional guarantees across SurrealDB + LiteLLM + OpenFGA.
- True distributed idempotency storage for all mutating APIs.
- Full SCIM RFC behavior (bulk, sort, full patch semantics).
- Production-grade retry queues for webhooks and audit export.

## Architecture summary

`Client -> API -> SurrealDB (identity) + LiteLLM keys + OpenFGA checks + OPA policies`

The API is stateless; persistent state must be externalized to production datastores.

## Dependency stack

- Python 3.12
- FastAPI / Uvicorn
- SurrealDB
- OpenFGA
- OPA
- Optional: Keycloak, VictoriaLogs, Lago, Langfuse

See `docs/architecture/runtime-dependencies.md` for runtime dependency details.

## Local quickstart

```bash
cp .env.example .env  # create values as needed
docker compose up -d --build
curl -s http://localhost:8500/health/live
```

## Run tests

```bash
pip install -r requirements.txt
pip install -r tests/requirements.txt
pytest -q
```

## Run with dependencies locally

```bash
uvicorn main:app --host 0.0.0.0 --port 8500 --reload
```

## Authorization and policy model

- **AuthN**: API bearer token (master/service), Keycloak userinfo checks for user paths.
- **AuthZ**: OpenFGA tuple checks for relationships.
- **Policy**: OPA decisions for conditional constraints.

## Known limitations

- Some endpoints still use master-key guardrail rather than fine-grained RBAC.
- SCIM coverage is partial.
- Retry/backoff strategy for downstream outages is basic.

## Additional docs

- `docs/audit/production-readiness-audit.md`
- `docs/audit/gap-matrix.md`
- `docs/operations/production-checklist.md`
- `deploy/README.md`
