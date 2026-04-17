# Autonomyx Agent Identity System

**Entra Agent ID spec — open-source implementation**

Three principal types, one platform:
- **Humans** → Keycloak (OIDC browser login)
- **Agents** → SurrealDB (first-class entity, own lifecycle)
- **Services** → Keycloak service accounts (M2M)

## Architecture

```
Human creates agent:
  POST /agents/create → SurrealDB + LiteLLM key + OpenFGA tuples

Agent authenticates:
  Authorization: Bearer sk-agent:name:tenant
  → LiteLLM validates → OpenFGA (WHO) → OPA (CONDITIONS) → Model

Human manages agents:
  Keycloak OIDC → JWT → /agents API → CRUD lifecycle
```

## Components

| Component | Purpose |
|---|---|
| `agent_identity.py` | Agent CRUD lifecycle (create, suspend, rotate, revoke) |
| `agent_discovery.py` | `/.well-known/agent-configuration` endpoint |
| `openfga_authz.py` | Relationship-based auth (WHO can access WHAT) |
| `opa_middleware.py` | Conditional policy engine (budget, DPDP, local-first) |
| `agent_bootstrap.py` | Pre-provision workflow agents on first deploy |

## Agent Attributes (Entra Agent ID spec)

| Attribute | Description |
|---|---|
| `agent_id` | Unique stable identifier |
| `agent_type` | workflow / ephemeral / mcp_tool |
| `sponsor_id` | Human who created the agent |
| `owner_ids` | Technical administrators |
| `manager_id` | Organizational hierarchy |
| `blueprint_id` | Template used to create agent |
| `allowed_models` | LLM models this agent can access |
| `budget_limit` | Maximum spend per period |
| `tpm_limit` | Tokens per minute rate limit |
| `expires_at` | TTL for ephemeral agents |
| `tenant_id` | Tenant isolation |

## Quick Start

```bash
cp .env.example .env
# Fill in service URLs and secrets
docker compose up -d
```

## Tests

```bash
pip install -r tests/requirements.txt
pytest tests/ -v
```

94 tests, 0 failures. Covers agent lifecycle, OpenFGA relationships, OPA policies, discovery endpoint.

## License

Part of the Autonomyx platform by OpenAutonomyx (OPC) Private Limited.
