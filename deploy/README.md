# Production Deployment Guide

## Recommended baseline

Use `deploy/docker-compose.prod.yml` as a starter for staging/prod-like deployments.

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file .env up -d --build
```

## Important production adjustments

1. Put API behind an HTTPS reverse proxy/API gateway.
2. Configure OpenFGA with Postgres (`OPENFGA_DATASTORE_URI`) — do not use memory mode.
3. Mount persistent volume backups for SurrealDB.
4. Restrict service ports to private network where possible.
5. Use external secret manager for all sensitive env vars.

## Example integration notes

- **Keycloak**: configure admin client for SCIM/group provisioning paths.
- **API gateway**: enforce request size limits and rate limits.
- **OPA/OpenFGA**: pin model/policy versions per release.
