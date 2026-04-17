# Autonomyx Agent Identity Specification v1.0
## A Vendor-Neutral Standard for AI Agent Identity

**Authors:** Chinmay, OpenAutonomyx (OPC) Private Limited
**Date:** April 17, 2026
**Status:** Draft — Reference Implementation Complete (98 tests passing)
**Repository:** github.com/openautonomyx/autonomyx-agent-identity

---

## Abstract

As AI agents become autonomous participants in software systems — making API calls, accessing databases, spending money, and acting on behalf of humans — the question of *who is this agent?* becomes as critical as *who is this user?*

No vendor-neutral standard currently defines what an AI agent IS as an identity principal. Microsoft's Entra Agent ID addresses this for the Azure ecosystem. OAuth 2.0 and OpenID Connect handle human and service identity. The Agent Auth Protocol defines how agents authenticate to services. But nothing defines the **agent as a first-class entity** in an open, implementable way.

This specification fills that gap.

---

## 1. The Problem

### 1.1 Current Identity Landscape

| Principal Type | Standard | Mature? |
|---|---|---|
| Human users | OIDC / OAuth 2.0 / SAML | ✅ 15+ years |
| Service accounts | OAuth 2.0 Client Credentials | ✅ 10+ years |
| **AI Agents** | **None** | ❌ |

### 1.2 Why Existing Standards Don't Work for Agents

**OAuth 2.0 Client Credentials** treats agents as "applications" — static, long-lived, identical to backend services. But agents are:
- **Created dynamically** by humans at runtime, not registered by administrators
- **Ephemeral** — some live for hours, not years
- **Sponsored** — always created by and accountable to a human
- **Scoped** — restricted to specific models, budgets, and data access
- **Auditable** — every action must be traceable to both the agent AND its human sponsor

**Keycloak service accounts**, **Auth0 M2M tokens**, and **AWS IAM roles** all model agents as variations of "application." None capture the agent-specific concepts of sponsorship, blueprints, ephemeral lifecycle, or model-level access control.

### 1.3 What Microsoft Gets Right (and Wrong)

Microsoft's Entra Agent ID (GA 2025) correctly identifies agents as a new principal type with:
- Unique identity separate from users and apps
- Sponsor relationship (human accountability)
- Blueprint pattern (templates for agent creation)
- Three-role admin model (owner, sponsor, manager)
- Ephemeral lifecycle with TTL

What Entra gets wrong:
- **Proprietary** — requires Azure Active Directory
- **No open spec** — implementation details locked to Microsoft Graph API
- **No billing integration** — doesn't address per-agent spend tracking
- **No policy engine** — conditional access is Entra-specific, not portable

---

## 2. The Autonomyx Agent Identity Model

### 2.1 Design Principles

1. **Agents are first-class entities**, not users, not service accounts, not tokens with extra claims
2. **Human sponsorship is mandatory** — every agent has a human who created it and is accountable for it
3. **Right-sized access by default** — agents start with zero access, explicitly granted per model/tenant
4. **Ephemeral is natural** — agents can have TTLs; expiry is a feature, not an edge case
5. **Billing is identity** — per-agent spend tracking is part of the identity model, not a bolt-on
6. **Vendor-neutral** — implementable on any identity provider, any policy engine, any database

### 2.2 The Three Principal Types

```
┌─────────────────────────────────────────────────────┐
│                 Identity Platform                    │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │  HUMAN   │  │  AGENT   │  │ SERVICE  │         │
│  │          │  │          │  │          │         │
│  │ Store:   │  │ Store:   │  │ Store:   │         │
│  │ Keycloak │  │ SurrealDB│  │ Keycloak │         │
│  │          │  │          │  │          │         │
│  │ Auth:    │  │ Auth:    │  │ Auth:    │         │
│  │ OIDC/JWT │  │ API Key  │  │ Client   │         │
│  │          │  │          │  │ Creds    │         │
│  │ Created: │  │ Created: │  │ Created: │         │
│  │ Self     │  │ By Human │  │ By Admin │         │
│  └──────────┘  └──────────┘  └──────────┘         │
│                                                     │
│  Auth check: OpenFGA (WHO) → OPA (CONDITIONS)      │
└─────────────────────────────────────────────────────┘
```

**Why separate stores?**

Humans live in Keycloak because they need OIDC browser flows, SSO federation, SAML, password reset — features purpose-built for human interaction. Forcing agents into Keycloak means treating them as "users without passwords" — an impedance mismatch that leaks complexity.

Agents live in SurrealDB because they need graph relationships (sponsor → agent → tenant → model), fast creation/deletion, custom attributes, and no OIDC overhead. SurrealDB's multi-model (document + graph + vector) fits agent identity natively.

Services stay in Keycloak because they ARE the traditional M2M use case — OAuth Client Credentials works perfectly for background services.

### 2.3 Agent Attributes

| Attribute | Type | Required | Description |
|---|---|---|---|
| `agent_id` | UUID | ✅ | Unique, stable, never reused |
| `agent_name` | string | ✅ | Human-readable identifier |
| `agent_type` | enum | ✅ | `workflow` / `ephemeral` / `mcp_tool` |
| `sponsor_id` | string | ✅ | Human who created this agent — mandatory |
| `owner_ids` | string[] | | Technical administrators who can modify config |
| `manager_id` | string | | Organisational hierarchy manager |
| `blueprint_id` | string | | Template this agent was created from |
| `tenant_id` | string | ✅ | Tenant isolation boundary |
| `allowed_models` | string[] | ✅ | Explicit model allowlist — no default access |
| `budget_limit` | float | | Maximum spend per budget period |
| `tpm_limit` | int | | Tokens per minute rate limit |
| `expires_at` | datetime | | TTL for ephemeral agents — null = persistent |
| `status` | enum | ✅ | `active` / `suspended` / `revoked` |
| `created_at` | datetime | ✅ | Immutable creation timestamp |
| `last_active_at` | datetime | | Last API call timestamp |
| `metadata` | object | | Extensible custom attributes |

### 2.4 Why Each Attribute Exists

**`agent_id` (UUID, required):**
Agents must be uniquely identifiable across the platform. UUIDs ensure no collision even in multi-tenant environments. Never reuse IDs — revoked agents keep their ID for audit trail.

**`agent_type` (enum, required):**
- `workflow`: Long-lived agents running automated processes. Always-on, scheduled, persistent state.
- `ephemeral`: Short-lived agents for one-time tasks. Have TTL, auto-expire, no persistent state.
- `mcp_tool`: Agents that expose capabilities via Model Context Protocol. Bridge between LLMs and external systems.

Each type implies different lifecycle, monitoring, and billing behaviour. Workflow agents get persistent budget tracking. Ephemeral agents get auto-cleanup. MCP tools get capability-based access.

**`sponsor_id` (string, required):**
The human who created and is accountable for this agent. MANDATORY — no orphan agents. If the sponsor is deactivated, all their agents are suspended. This is the single most important design decision: *every agent has a human who answers for it.*

**Why mandatory:** In enterprise deployments, compliance teams need to answer "who is responsible for this agent that accessed our customer data?" The answer must always be a human, not another agent.

**`allowed_models` (string[], required):**
Agents start with ZERO model access. Every model must be explicitly granted. This is the opposite of "allow all by default" — right-sized access from creation.

**Why not inherit from tenant?** Tenants may have access to 20 models, but a fraud-detection agent only needs one reasoning model. Granting all 20 is a security risk and a billing risk.

**`budget_limit` (float, optional):**
Per-agent spend cap per billing period. When reached, the agent's API calls are rejected by the policy engine. Billing is identity — you can't have agent identity without knowing what the agent costs.

**`expires_at` (datetime, optional):**
Ephemeral agents MUST have an expiry. Workflow agents MAY have one. After expiry, the agent's API key is automatically revoked. No manual cleanup needed.

---

## 3. Authorization Model

### 3.1 Two-Layer Auth (OpenFGA + OPA)

```
Request arrives
  │
  ▼
OpenFGA — WHO can access WHAT (relationships)
  ├── agent:X can_use model:qwen3-30b?
  ├── agent:X member tenant:acme?
  └── user:Y sponsor agent:X?
  │
  ▼ (if allowed)
OPA — CONDITIONS under which access is granted (policies)
  ├── agent status == active?
  ├── agent not expired?
  ├── budget not exceeded?
  ├── TPM not exceeded?
  ├── local model available → use local (not cloud)?
  ├── PII detected → no US cloud (DPDP Act)?
  └── prompt not too large for model?
  │
  ▼ (if allowed)
Route to model
```

### 3.2 Why Two Layers (Not One)

**OpenFGA** answers "WHO" questions using relationship graphs (Google Zanzibar model). It's fast (<10ms), indexed, and handles complex delegation chains. But it can't evaluate runtime conditions like "is the budget exceeded right now?"

**OPA** answers "SHOULD WE" questions using Rego policy-as-code. It evaluates conditions against live state — budgets, time windows, system health, content inspection. But it's not designed for relationship graphs.

Together they're complete. Separately, each has blind spots.

### 3.3 Why Not AuthZEN?

AuthZEN (OpenID Foundation) standardises PDP↔PEP communication — how to ASK an authorization question. It does NOT define:
- What an agent IS
- How agents are created or managed
- Agent-specific attributes (sponsor, blueprint, TTL)
- Billing integration

AuthZEN could be adopted as the **transport layer** for our authorization checks. The specs are complementary, not competing.

---

## 4. Agent Lifecycle

### 4.1 Creation

```
POST /agents/create
  │
  ├── Validate: sponsor exists in Keycloak
  ├── Validate: sponsor has permission to create agents
  ├── SurrealDB: CREATE agent record
  ├── LiteLLM: Create scoped Virtual Key
  ├── OpenFGA: Write relationship tuples
  │     agent:X can_use model:Y
  │     agent:X member tenant:Z
  │     user:sponsor sponsor agent:X
  └── Return: agent_id + API key (shown ONCE)
```

**Why Keycloak is NOT involved in agent creation:**
Agents don't need OIDC flows, password management, or federation. Creating a Keycloak entity for each agent adds latency, complexity, and impedance mismatch. The agent's auth token is a LiteLLM Virtual Key — lightweight, scoped, revocable.

### 4.2 Authentication

```
Agent makes API call:
  Authorization: Bearer sk-agent:fraud-sentinel:tenant-acme
  │
  ├── LiteLLM validates Virtual Key
  ├── Resolves: agent_id, tenant_id, allowed_models
  ├── OpenFGA check: does this agent have this model?
  ├── OPA check: conditions met?
  └── Route to model (or reject with reason)
```

### 4.3 Suspension / Reactivation / Rotation / Revocation

| Action | What happens | Reversible? |
|---|---|---|
| Suspend | Virtual Key invalidated, agent record stays | ✅ Reactivate restores access |
| Reactivate | New Virtual Key issued, status → active | — |
| Rotate | Old key invalidated, new key issued, same agent_id | ✅ Transparent to OpenFGA |
| Revoke | Key invalidated, status → revoked, record preserved for audit | ❌ Permanent |

### 4.4 Expiry (Ephemeral Agents)

A background worker checks `expires_at` for all ephemeral agents. When expired:
1. Virtual Key is revoked
2. Status set to `expired`
3. OpenFGA tuples are removed
4. Agent record preserved in SurrealDB for audit (never deleted)

---

## 5. Implementation Architecture

### 5.1 Why These Specific Technologies

**SurrealDB for Agent Registry:**
- Multi-model: document + graph + vector in one DB
- Native graph queries: `RELATE agent:X->belongs_to->tenant:Y`
- LIVE SELECT for real-time agent status monitoring
- Self-hosted, no cloud dependency
- License: BSL 1.1 (acceptable for internal use; converts to Apache 2.0 after 4 years)

*Alternative considered:* PostgreSQL with JSONB. Rejected because graph relationships (sponsor → agent → tenant → model) are clumsy in relational model. Joins scale poorly when every authorization check needs multiple hops.

**OpenFGA for Relationship-Based Authorization:**
- Google Zanzibar model — battle-tested at Google scale
- CNCF Incubating — vendor-neutral governance
- Apache 2.0 license
- <10ms check latency
- Native support for "agent as principal" (agents treated same as users in tuple format)

*Alternative considered:* OPA alone. Rejected because encoding relationship graphs in Rego is verbose and slow. OPA excels at CONDITIONS, not RELATIONSHIPS.

**OPA for Conditional Policy:**
- CNCF Graduated — highest trust level
- Apache 2.0 license
- Rego is declarative, testable, git-versionable
- <5ms evaluation latency
- 10 policy rules cover: budget, DPDP, local-first, TTL, TPM, prompt size

*Alternative considered:* OpenFGA conditions. Rejected because OpenFGA v1.8 conditions are limited — can't evaluate live budget state or call external health endpoints.

**Keycloak for Human Identity:**
- Apache 2.0, Red Hat/IBM backed
- 15 years production hardening
- SAML + OIDC + social login
- Enterprise SSO federation
- Fine-grained RBAC/ABAC

*Alternative considered:* Logto (lighter, better UX). Rejected because: (1) no SAML support — blocks enterprise customers using Azure AD/Okta, (2) 3 years old vs 15 — immature for identity infrastructure, (3) already integrated in our stack.

*Alternative considered:* Better Auth (Agent Auth plugin). Rejected because: (1) TypeScript only — our stack is Python, (2) agent auth plugin is beta/"not yet stable", (3) library not a server — requires building an app around it.

**LiteLLM for Gateway + Agent Auth Tokens:**
- MIT license (watch for changes — BerriAI is YC-backed)
- Virtual Keys ARE agent auth tokens — scoped, budgeted, revocable
- OpenAI-compatible API — agents use standard SDK
- Built-in spend tracking per key

*Alternative considered:* Custom gateway. Rejected because LiteLLM's Virtual Key system, model routing, fallback chains, and provider support would take months to rebuild.

### 5.2 What This Specification Does NOT Cover

- **Transport protocol** between agents and services (use Agent Auth Protocol or OAuth 2.0)
- **Discovery mechanism** for finding agent services (see `/.well-known/agent-configuration`)
- **Wire format** for agent-to-agent communication (use MCP or A2A)
- **Training data consent** (separate from identity — handled by ToS and opt-in flags)
- **Content safety** (use OPA policies + guardrails, not identity layer)

---

## 6. Comparison to Existing Approaches

| Capability | Entra Agent ID | OAuth 2.0 CC | Agent Auth Protocol | **This Spec** |
|---|---|---|---|---|
| Agent as first-class entity | ✅ | ❌ | ✅ | ✅ |
| Vendor-neutral | ❌ Azure | ✅ RFC | ✅ | ✅ |
| Human sponsor mandatory | ✅ | ❌ | ❌ | ✅ |
| Blueprint/template pattern | ✅ | ❌ | ❌ | ✅ |
| Three-role admin model | ✅ | ❌ | ❌ | ✅ |
| Ephemeral TTL | ✅ | ❌ | ❌ | ✅ |
| Per-agent billing | ❌ | ❌ | ❌ | ✅ |
| Model-level access control | ❌ | ❌ | ❌ | ✅ |
| DPDP/GDPR policy engine | ❌ | ❌ | ❌ | ✅ |
| Reference implementation | Azure only | Many | Better Auth | Open source |
| Test coverage | N/A | N/A | Minimal | 98 tests |

---

## 7. Reference Implementation

**Repository:** github.com/openautonomyx/autonomyx-agent-identity

| Component | File | Tests |
|---|---|---|
| Agent CRUD lifecycle | agent_identity.py | 35 tests |
| Keycloak JWT verification | keycloak_auth.py | 4 tests |
| OpenFGA authorization | openfga_authz.py | 28 tests |
| OPA policy engine | opa_middleware.py | 12 tests |
| Agent discovery | agent_discovery.py | 9 tests |
| Agent bootstrap | agent_bootstrap.py | 15 tests |
| OPA policies (Rego) | opa/policy.rego | 21 rules |
| OpenFGA model | openfga/model.fga | 4 types, 8 relations |
| **Total** | **8 files** | **98 tests, 0 failures** |

### Deployed at:
- Agent Identity API: `https://id.unboxd.cloud`
- Keycloak: `https://auth.unboxd.cloud`
- LiteLLM Gateway: `https://llm.openautonomyx.com`

---

## 8. Future Work

1. **AuthZEN transport layer** — adopt OpenID AuthZEN for standardised PDP↔PEP communication
2. **Agent Auth Protocol compliance** — align `/.well-known/agent-configuration` with the emerging open standard
3. **Temporal orchestration** — durable workflow execution for agent lifecycle events
4. **Agent-to-agent delegation** — agent A can delegate scoped access to agent B (Zanzibar transitive relations)
5. **Verifiable credentials** — W3C VCs for portable agent identity across platforms
6. **Formal IETF draft** — submit as Internet-Draft for standardisation track

---

## 9. License

This specification is published under Creative Commons Attribution 4.0 (CC BY 4.0). The reference implementation is open source under the repository license.

**OPENAUTONOMYX (OPC) PRIVATE LIMITED**
No. 78/9, Outer Ring Road, Varthur Hobli, Bellandur, Bangalore South, Bangalore – 560103, Karnataka, India
CIN: U62010KA2026OPC215666
