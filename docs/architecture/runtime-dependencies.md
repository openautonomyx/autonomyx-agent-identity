# Runtime Dependencies

## Required

- **FastAPI API service**: main control-plane API.
- **SurrealDB**: source of truth for agent records/audit storage.
- **LiteLLM gateway**: key generation/revocation and model gateway.

## Strongly recommended for production

- **OpenFGA**: relationship-based authorization decisions.
- **OPA**: conditional policy evaluation.
- **Reverse proxy / API gateway**: TLS termination, rate limiting, WAF, request size controls.

## Optional integrations

- **Keycloak**: user/service authn and tenant/group modeling.
- **VictoriaLogs**: immutable audit export stream.
- **Lago**: tenant billing plan wiring.
- **Langfuse**: observability integration for tenant orgs.

## Dependency health semantics

- `/health/live`: process alive (no dependency checks).
- `/health/ready`: checks SurrealDB (if configured), OPA, and OpenFGA; returns `503` on degraded state.

## Network/security expectations

- All service-to-service traffic should run on private network segments.
- Secrets must be injected via environment/secret manager; never committed.
- OpenFGA/OPA admin surfaces should not be publicly exposed.
