# Production Readiness Audit — Autonomyx Agent Identity Plane

## Executive summary

The repository already has substantial implementation breadth (agent identity lifecycle, discovery, OpenFGA, OPA, audit/webhooks/SCIM surfaces, tests, and containerization). The largest gaps were production hardening concerns: unsafe defaults, weak readiness semantics, minimal request observability, insecure webhook delivery pattern, missing CI quality gates, and unclear production deployment guidance.

This remediation pass upgrades core operational posture while preserving architecture intent.

## Current architecture overview

- FastAPI API process (`main.py`) with routers for identity, discovery, authz, policy, audit, bulk, webhooks, and SCIM.
- SurrealDB as primary identity/audit store.
- OpenFGA for relationship authorization.
- OPA for conditional policy.
- Background expiry loop for TTL-driven identity expiration.
- Optional integrations with Keycloak, VictoriaLogs, Lago, and Langfuse.

## Implemented capabilities

- Agent lifecycle endpoints including create/suspend/reactivate/rotate/revoke.
- OpenFGA tuple write/revoke/check + model listing.
- OPA policy evaluate endpoint and callback utility.
- Webhook registration/listing and event fanout.
- SCIM-like Users/Groups APIs.
- Audit event write/query APIs.
- Expiry worker implementation.
- Unit/integration-oriented test suite.

## Partially implemented capabilities

- SCIM: partial RFC coverage (no bulk support; partial patch behavior).
- Audit durability: primary write present, external sink best-effort.
- Resilience: downstream failures handled inconsistently.
- Multi-tenant enforcement: represented in model, not uniformly enforced at every endpoint.
- Error payload consistency: previously ad hoc, now partially standardized at global handler level.

## Missing capabilities

- Strong distributed idempotency persistence for mutating APIs.
- Full per-endpoint role-based authz and policy integration.
- Queue-backed webhook delivery retries/dead-letter handling.
- Complete transactional orchestration across SurrealDB/LiteLLM/OpenFGA.
- Production-grade migration/bootstrap tooling for schema and tuples.

## Security risks

- Prior unsafe defaults and permissive startup behavior in non-dev environments.
- Webhooks previously sent raw shared secret headers without signatures.
- Some endpoints still rely on shared master-key semantics.

## Reliability risks

- Background expiry loop previously swallowed exceptions without telemetry.
- Readiness endpoint missing service dependency checks.
- External dependency degradation behavior under-documented.

## Scalability risks

- In-process state for registered webhooks.
- Synchronous fanout per webhook target without queueing.
- SCIM and list endpoints have limited advanced pagination/filtering behavior.

## Developer experience gaps

- No single source documenting runtime dependencies and production checklist.
- CI pipeline and quality gates were absent.
- Test dependencies mismatched local runtime in some environments.

## Documentation gaps

- README previously overstated maturity and lacked explicit production-vs-experimental boundaries.
- Production deployment topology and security checklist were incomplete.

## Prioritized remediation roadmap

### P0 (must fix now)
1. Enforce typed config validation and production fail-fast.
2. Add readiness/liveness split and dependency checks.
3. Add request correlation and baseline structured logging.
4. Add CI workflow with lint/test/security checks.
5. Harden webhook delivery with HMAC signature headers.

### P1 (should fix soon)
1. Introduce persisted idempotency-key store (DB-backed).
2. Implement robust tenant-aware authz for all CRUD/query endpoints.
3. Add retry queue/dead-letter policy for webhook and audit sink delivery.
4. Expand SCIM compliance (bulk/sort/patch parity).

### P2 (later)
1. Replace coarse master-key administration with scoped service RBAC.
2. Add Kubernetes manifests/Helm packaging and rollout strategy.
3. Add SLO-backed dashboards and alerting runbooks.
