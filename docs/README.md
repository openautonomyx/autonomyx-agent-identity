# Autonomyx Identity Platform

> **The Okta For Agentic Enterprises**
>
> Unified identity management for humans and AI agents.
> SCIM 2.0 · OpenFGA · OPA · Keycloak · APISIX

## Overview

The Autonomyx Identity Platform is an open-source identity and access management system designed for the AI agent era. It treats AI agents as first-class entities — not service accounts — with their own lifecycle, credentials, authorization, and audit trail.

**Three principal types, one control plane:**

| Principal | Store | Auth Method |
|-----------|-------|-------------|
| Humans | Keycloak (OIDC/SAML) | Browser SSO, JWT |
| Agents | SurrealDB | LiteLLM Virtual Key |
| Services | Keycloak (Client Credentials) | M2M OAuth2 |

**Two-layer authorization:**

| Layer | Engine | Purpose |
|-------|--------|---------|
| WHO can access WHAT | OpenFGA (Zanzibar) | Relationship-based access control |
| Under WHAT conditions | OPA (Rego) | Budget, rate limits, compliance policies |

## Architecture

```
Human → Keycloak JWT → Identity API → SurrealDB + LiteLLM + OpenFGA
Agent → Virtual Key → APISIX Gateway → forward-auth → OpenFGA → OPA → Service
App   → SCIM 2.0   → Identity API → Keycloak (human) / SurrealDB (agent)
```

## Quick Start

```bash
# Clone
git clone https://github.com/openautonomyx/autonomyx-agent-identity.git
cd autonomyx-agent-identity

# Configure
cp .env.example .env
# Edit .env with your values

# Run
docker compose up -d

# Verify
curl http://localhost:8500/health
# {"status":"ok","service":"agent-identity"}
```

## API Reference

**Base URL:** `https://api.unboxd.cloud/identity` (via APISIX gateway)
**Auth:** `Authorization: Bearer <master_key_or_agent_key>`
**Docs:** `https://id.unboxd.cloud/docs` (interactive Swagger UI)

### Modules

| Module | Endpoints | Purpose |
|--------|-----------|---------|
| [Agent Identity](#agent-identity) | 8 | Create, manage, and lifecycle agents |
| [Authorization](#authorization-openfga) | 7 | Relationship-based access control |
| [Audit Log](#audit-log) | 4 | Immutable event trail (SurrealDB + VictoriaLogs) |
| [Blueprints](#blueprints) | 3 | Agent templates for stamping out agents |
| [Bulk Operations](#bulk-operations) | 2 | Mass suspend/revoke |
| [Webhooks](#webhooks) | 2 | Event notifications |
| [Policy (OPA)](#policy-opa) | 2 | Budget, rate limit, compliance checks |
| [SCIM 2.0](#scim-20) | 9 | Provision from any SCIM app (Okta, Azure AD, etc.) |
| [Discovery](#discovery) | 2 | Agent configuration document |
| [Gateway Auth](#gateway-auth) | 1 | APISIX forward-auth hook |
| [Health](#health) | 1 | Service health check |

**Total: 41 endpoints**

---

## Agent Identity

Implements the Autonomyx Agent Identity Specification v1.0 (Entra Agent ID model).

### Create Agent
```http
POST /agents/create
```
```json
{
  "agent_name": "fraud-sentinel",
  "agent_type": "workflow",
  "sponsor_id": "admin@company.com",
  "tenant_id": "tenant-acme",
  "allowed_models": ["ollama/qwen3:30b-a3b"],
  "budget_limit": 5.0,
  "tpm_limit": 10000
}
```
**Response:** Returns `agent_id`, `litellm_key` (shown once), `status: "active"`

### List Agents
```http
GET /agents?tenant_id=tenant-acme&status=active&agent_type=workflow
```

### Get Agent
```http
GET /agents/{agent_id}
```

### Suspend Agent
```http
POST /agents/{agent_id}/suspend
```
Revokes LiteLLM key, preserves identity. Can be reactivated.

### Reactivate Agent
```http
POST /agents/{agent_id}/reactivate
```
Issues new LiteLLM key. Same agent_id, new credentials.

### Rotate Key
```http
POST /agents/{agent_id}/rotate
```
Zero-downtime key rotation. New key issued before old key deleted.

### Revoke Agent
```http
DELETE /agents/{agent_id}
```
Permanent. LiteLLM key deleted. SurrealDB record retained for audit.

### Get Activity
```http
GET /agents/{agent_id}/activity?limit=50
```

---

## Authorization (OpenFGA)

Zanzibar-model relationship authorization.

### Grant Relationship
```http
POST /authz/grant
```
```json
{
  "user": "agent_identity:fraud-sentinel",
  "relation": "can_use_model",
  "object": "model:qwen3-30b-a3b"
}
```

### Revoke Relationship
```http
POST /authz/revoke
```

### Check Authorization
```http
POST /authz/check
```
```json
{
  "user": "agent_identity:fraud-sentinel",
  "relation": "can_use_model",
  "object": "model:qwen3-30b-a3b"
}
```
**Response:** `{"allowed": true}`

### List Agent Models
```http
GET /authz/agent/{agent_name}/models
```

### Grant Model Access
```http
POST /authz/agent/{agent_name}/grant-model/{model_name}
```

### Revoke Model Access
```http
POST /authz/agent/{agent_name}/revoke-model/{model_name}
```

### Gateway Auth (APISIX forward-auth)
```http
GET /authz/check-request
Headers: Authorization, X-Forwarded-Uri, X-Forwarded-Method
```
Called by APISIX on every API request. Returns 200 with `X-Agent-Id`, `X-Tenant-Id`, `X-Agent-Name` headers, or 401/403.

---

## Audit Log

Immutable audit trail. Dual-write to SurrealDB (queryable) and VictoriaLogs (dashboardable via Grafana).

### Query Events
```http
GET /audit/?agent_id=xxx&tenant_id=xxx&event_type=agent.created&limit=50
```

### Agent Trail
```http
GET /audit/agent/{agent_id}
```

### Sponsor Trail
```http
GET /audit/sponsor/{sponsor_id}
```

### Tenant Trail
```http
GET /audit/tenant/{tenant_id}
```

**Event types:** `agent.created`, `agent.suspended`, `agent.reactivated`, `agent.rotated`, `agent.revoked`, `agent.expired`, `agent.model_granted`, `agent.model_revoked`

---

## Blueprints

Templates for stamping out agents with pre-configured defaults.

### Create Blueprint
```http
POST /blueprints/create
```
```json
{
  "name": "fraud-detector-template",
  "agent_type": "workflow",
  "default_models": ["ollama/qwen3:30b-a3b"],
  "default_budget": 5.0,
  "default_tpm": 10000,
  "owner_id": "admin@company.com"
}
```

### List Blueprints
```http
GET /blueprints/
```

### Get Blueprint
```http
GET /blueprints/{blueprint_id}
```

---

## Bulk Operations

### Bulk Suspend
```http
POST /bulk/suspend
```
```json
{"agent_ids": ["agent-001", "agent-002", "agent-003"]}
```
**Response:** `{"succeeded": ["agent-001", "agent-002"], "failed": [{"agent_id": "agent-003", "error": "..."}]}`

### Bulk Revoke
```http
POST /bulk/revoke
```

---

## Webhooks

### Register Webhook
```http
POST /webhooks/register
```
```json
{
  "url": "https://your-app.com/hook",
  "events": ["agent.created", "agent.suspended"],
  "secret": "your-webhook-secret"
}
```

### List Webhooks
```http
GET /webhooks/
```

---

## Policy (OPA)

### Evaluate Policy
```http
POST /policy/evaluate
```

### Policy Health
```http
GET /policy/health
```

---

## SCIM 2.0

RFC 7644 compliant. Connect any SCIM app (Okta, Azure AD, Google Workspace, JumpCloud) to provision and deprovision identities.

### Service Provider Config
```http
GET /scim/v2/ServiceProviderConfig
```

### Schemas
```http
GET /scim/v2/Schemas
```

### Resource Types
```http
GET /scim/v2/ResourceTypes
```

### List Users (Humans + Agents)
```http
GET /scim/v2/Users?count=100
```

### Create User
```http
POST /scim/v2/Users
```
```json
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "userName": "fraud-sentinel",
  "displayName": "Fraud Sentinel Agent",
  "active": true,
  "urn:ietf:params:scim:schemas:extension:autonomyx:2.0:User": {
    "entityType": "agent",
    "tenantId": "tenant-acme",
    "sponsorId": "admin@acme.com",
    "agentType": "workflow"
  }
}
```

### Get User
```http
GET /scim/v2/Users/{id}
```

### Update User (Patch)
```http
PATCH /scim/v2/Users/{id}
```
```json
{
  "Operations": [{"op": "replace", "path": "active", "value": false}]
}
```
Setting `active: false` suspends agents or disables Keycloak users.

### Delete User
```http
DELETE /scim/v2/Users/{id}
```
Revokes agents or removes Keycloak users.

### List Groups (Tenants)
```http
GET /scim/v2/Groups
```

### Create Group (Tenant)
```http
POST /scim/v2/Groups
```
```json
{"displayName": "Acme Corp"}
```

---

## Discovery

### Agent Configuration
```http
GET /.well-known/agent-configuration
GET /.well-known/agent-configuration.json
```
Returns the agent discovery document per the Agent Auth Protocol spec.

---

## Health

```http
GET /health
```
```json
{"status": "ok", "service": "agent-identity"}
```

---

## Infrastructure

### Server 2 (unboxd.cloud) — Identity Stack

| Service | URL | Purpose |
|---------|-----|---------|
| Identity API | https://id.unboxd.cloud | Agent CRUD, SCIM, authz |
| APISIX Gateway | https://api.unboxd.cloud | 26-route API gateway with forward-auth |
| Identity Console | https://console.unboxd.cloud | Next.js + Carbon admin UI |
| Keycloak | https://auth.unboxd.cloud | Human SSO (OIDC/SAML) |
| OpenFGA | https://fga.unboxd.cloud | Relationship authorization |
| OPA | https://opa.unboxd.cloud | Policy engine |
| Infisical | https://secrets.unboxd.cloud | Secret management |
| Docker Registry | https://registry.unboxd.cloud | 54 images (13 apps + 41 skills) |
| Liferay Portal | https://portal.unboxd.cloud | Multi-tenant admin portal |
| WordPress | https://cms.unboxd.cloud | Content management |
| Nextcloud | https://next.unboxd.cloud | File management |

### AgentNxt Products (agnxxt.com)

| Product | URL | Purpose |
|---------|-----|---------|
| AgentCode | https://code.agnxxt.com | AI coding platform |
| AgentCrew | https://crew.agnxxt.com | Multi-agent orchestration |
| AgentStudio | https://studio.agnxxt.com | Visual agent builder |
| AgentFlow | https://flow.agnxxt.com | Workflow automation |
| AgentChat | https://chat.agnxxt.com | AI chat interface |
| AgentSearch | https://search.agnxxt.com | AI-powered search |
| AgentNotebook | https://notebook.agnxxt.com | AI notebook |
| Identity Console | https://console.agnxxt.com | Agent identity management |

### Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Agent identity store | SurrealDB | Agents are first-class, not service accounts |
| Relationship auth | OpenFGA (CNCF) | Zanzibar model, vendor-neutral |
| Policy engine | OPA (CNCF Graduated) | Rego, vendor-neutral |
| Human auth | Keycloak | Enterprise SSO, SAML, OIDC |
| API gateway | APISIX (Apache) | Forward-auth, rate limiting, Apache 2.0 |
| Provisioning | SCIM 2.0 (RFC 7644) | Standard protocol, 7000+ app compatibility |
| Audit log sink | VictoriaLogs | Apache 2.0 (not Loki — AGPL) |
| Secret management | Infisical | Multi-tenant, Apache 2.0 |
| LLM gateway | LiteLLM | OpenAI-compatible, Virtual Keys |
| Container registry | Self-hosted (registry:2) | No vendor lock-in |

---

## Testing

```bash
# Unit tests (144 tests)
pytest tests/ -m "not integration"

# Integration tests with Testcontainers (14 tests)
# Requires Docker — spins up real SurrealDB + OpenFGA
pytest tests/ -m integration

# All tests
pytest tests/
```

**Total: 158 tests, 0 failures**

---

## Integration Guide

### Connect any SCIM app
1. In your app (Okta, Azure AD, etc.), add a SCIM provisioning integration
2. Set base URL: `https://api.unboxd.cloud/identity/scim/v2`
3. Set auth: Bearer token with your master key
4. Map user attributes to SCIM schema
5. Enable provisioning — users/agents auto-sync

### Connect via APISIX gateway
All services accessible through `https://api.unboxd.cloud/{service}/*`
Auth header required on every request. Forward-auth checks OpenFGA.

### Connect via OpenAPI
Interactive docs: `https://id.unboxd.cloud/docs`
OpenAPI spec: `https://id.unboxd.cloud/openapi.json`

---

## License

Apache 2.0 — all components are vendor-neutral and open-source.
