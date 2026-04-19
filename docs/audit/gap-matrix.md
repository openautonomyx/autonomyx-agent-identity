# Gap Analysis Matrix

| Area | Current state | Evidence in repo | Risk | Recommended fix | Priority |
|---|---|---|---|---|---|
| API completeness | Core endpoints exist; semantics vary | `agent_identity.py`, `scim.py`, `bulk_ops.py` | Consumer confusion | Standardize response/error contracts and pagination patterns | P1 |
| Identity lifecycle | Create/suspend/reactivate/revoke implemented | `agent_identity.py` | Partial authz granularity | Add per-role endpoint authorization and idempotency store | P1 |
| AuthN | Master token + Keycloak helper paths | `keycloak_auth.py` | Shared-key blast radius | Move to scoped service credentials/JWT validation everywhere | P1 |
| AuthZ | OpenFGA checks present | `openfga_authz.py` | Misconfig fail-open risk historically | Keep fail-closed and validate store/model at startup | P0 |
| Policy enforcement | OPA hook + evaluate endpoint | `opa_middleware.py` | Downstream outage denial behavior may surprise | Add explicit graceful-degradation modes by env | P1 |
| SCIM | Basic Users/Groups implemented | `scim.py` | Incomplete RFC support | Expand patch/filter/sort/bulk behavior and conformance tests | P1 |
| Webhooks | Fanout implemented | `webhooks.py` | Tampering/replay risk | Added HMAC timestamp signature; add retry queue next | P0 |
| Audit logs | DB + optional external sink | `audit.py` | Sink loss is silent best-effort | Add durable async exporter and delivery metrics | P1 |
| Discovery | Implemented | `agent_discovery.py` | Drift with actual runtime config | Add startup checks + contract tests | P2 |
| Bulk operations | Suspend/revoke bulk endpoints | `bulk_ops.py` | No partial retry strategy | Add operation IDs + async job model | P2 |
| Expiry/revocation | Worker exists; query bug fixed | `expiry_worker.py` | Missed expirations if worker down | Move to scheduled job runner with lease locking | P1 |
| Database/persistence | SurrealDB used; prod guidance weak | `docker-compose.yml` | Ephemeral/non-prod defaults | Added prod compose; document durable config and backups | P0 |
| OpenFGA integration | Integrated and test-covered | `openfga_authz.py`, `openfga/*` | Store bootstrap drift | Add automated model+tuple bootstrap checks in CI/deploy | P1 |
| OPA integration | Policy evaluation integrated | `opa_middleware.py`, `opa/policy.rego` | Policy/version drift | Pin bundle versioning and policy tests in CI | P1 |
| Secrets/config | Env var driven; now typed validation | `settings.py` | Runtime misconfig | Keep startup validation and prod strict mode | P0 |
| Error handling | Previously inconsistent; now global fallback | `main.py` | Mixed detail exposure | Adopt common API error schema across routers | P1 |
| Input validation | Good Pydantic baseline | `agent_identity.py`, `webhooks.py` | Some fields too permissive | Tighten schemas/enums and normalize IDs | P1 |
| Idempotency | Limited/no durable strategy | repo-wide | Duplicate creates on retries | Add DB-backed idempotency table + middleware | P1 |
| Pagination/filtering | Basic in some endpoints only | `agent_identity.py`, `scim.py` | Large query load | Add consistent cursor/offset contracts | P2 |
| Rate limiting | Not implemented | repo-wide | Abuse/cost risk | Integrate gateway or middleware rate limits | P1 |
| Observability | Improved request IDs + health split | `observability.py`, `main.py` | No metrics exporter yet | Add Prometheus metrics and dashboards | P1 |
| CI/CD | Added baseline CI workflow | `.github/workflows/ci.yml` | Coverage gaps may remain | Add dependency update + release workflows | P1 |
| Local developer setup | Works via compose | `docker-compose.yml`, `README.md` | Tooling assumptions | Add `make` targets and onboarding script | P2 |
| Production deployment | New prod compose + deploy docs | `deploy/*` | Need orchestration patterns | Add Kubernetes manifests/Helm starter | P2 |
| Testing | Solid unit suite; gaps remain | `tests/*` | Outage path regressions | Added targeted hardening tests; expand integration chaos tests | P1 |
| Documentation | Major clarity improvements added | `README.md`, `docs/*` | Doc drift risk | Add docs review checklist in PR template | P2 |
