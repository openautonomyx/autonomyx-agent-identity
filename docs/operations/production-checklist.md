# Production Checklist

## Before first deploy

- [ ] Set `APP_ENV=prod`.
- [ ] Set required vars: `LITELLM_MASTER_KEY`, `SURREAL_URL`, `OPENFGA_STORE_ID`.
- [ ] Configure `CORS_ALLOW_ORIGINS` explicitly.
- [ ] Ensure SurrealDB uses persistent volume and backup strategy.
- [ ] Ensure OpenFGA uses Postgres (not memory) in production.
- [ ] Configure TLS termination at ingress/reverse proxy.
- [ ] Validate webhook secrets for all downstream consumers.

## Security

- [ ] Rotate all service credentials before go-live.
- [ ] Restrict admin endpoints behind private network and RBAC.
- [ ] Enable audit ingestion retention controls.
- [ ] Add rate limiting at edge and/or app layer.

## Reliability

- [ ] Monitor `/health/ready` and alert on 503.
- [ ] Configure restart policy and graceful shutdown budgets.
- [ ] Verify OPA/OpenFGA outage behavior with staging game-day tests.
- [ ] Validate expiry worker is running exactly once per shard/tenant policy.

## Observability

- [ ] Capture and index `X-Request-Id` in logs.
- [ ] Export API request and dependency metrics.
- [ ] Build dashboards for authz denies, policy denies, webhook failures.

## Release quality gates

- [ ] CI green: lint + tests + static security checks.
- [ ] Reviewed `docs/audit/gap-matrix.md` impact for changed areas.
- [ ] Updated README/docs for any behavior changes.
