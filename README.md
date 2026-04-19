# AutonomyX Agent Identity Plane

AutonomyX Agent Identity Plane is an open-source platform for managing non-human identities (AI agents) across registration, trust, authorization, policy enforcement, and lifecycle controls.

This repository now includes:
- a FastAPI backend for identity, authz, policy, audit, webhooks, and SCIM-style modules,
- a production-oriented operations baseline,
- and a new Next.js product website + admin console experience.

## What this project is

This service manages machine identities for agents and enforces runtime access constraints using:
- **Keycloak** for human/service authentication.
- **SurrealDB** for agent identity state.
- **OpenFGA** for relationship authorization (who can use what).
- **OPA** for conditional policy evaluation (budget, expiry, model constraints).

## Product surfaces

### 1) Public website (`frontend/app`)
Pages implemented:
- Home
- Product
- Architecture
- Security
- Developers
- Integrations
- Pricing placeholder
- Open Source / Community
- Contact / Demo placeholder

### 2) Admin console (`/console`)
Views implemented:
- Dashboard
- Agents list
- Agent detail
- Registrations
- Discovery
- Policies
- Audit logs
- Webhooks
- Blueprints
- Integrations
- Settings
- System health

> Current UI is intentionally API-ready but mostly mock-backed to enable immediate demoability while backend contracts are finalized.

## Screenshots
- Placeholder: run the frontend locally and capture pages for docs/screenshots as needed.

## Architecture summary

`Client/UI -> FastAPI control plane -> SurrealDB + OpenFGA + OPA + optional Keycloak/gateway/webhook consumers`

The API is stateless; persistent state must be externalized to production datastores.

## Tech stack

### Backend
- Python 3.12, FastAPI, Uvicorn
- SurrealDB
- OpenFGA
- OPA

### Frontend
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Mock data service layer (`frontend/lib/site-data.ts`)

## Local quickstart (backend)

```bash
cp .env.example .env  # create values as needed
docker compose up -d --build
curl -s http://localhost:8500/health/live
```

## Frontend quickstart

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` for the website and `http://localhost:3000/console` for the admin UI.

## How frontend connects to backend

- Current state: pages are rendered with typed mock data for consistent demos.
- Intended integration: replace `frontend/lib/site-data.ts` with API clients per domain module (agents, policy, audit, webhooks).
- Integration boundary is documented in `docs/ui/ui-architecture.md`.

## Test and quality checks

```bash
pip install -r requirements.txt
pip install -r tests/requirements.txt
pytest -q
```

Frontend checks:

```bash
cd frontend
npm run lint
npm run typecheck
```

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
- Full console authentication and live backend wiring.

## UI/UX documentation
- `docs/ui/ui-architecture.md`
- `docs/ui/design-system.md`
- `docs/ui/information-architecture.md`
- `docs/ui/console-pages.md`
- `docs/ui/website-messaging.md`

## Additional docs
- `docs/audit/production-readiness-audit.md`
- `docs/audit/gap-matrix.md`
- `docs/operations/production-checklist.md`
- `deploy/README.md`
