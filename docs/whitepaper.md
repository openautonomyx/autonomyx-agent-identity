# Autonomyx Agent Identity Model and Reference Architecture
## An Open Framework for AI Agent Identity Management

**Authors:** Chinmay, OpenAutonomyx (OPC) Private Limited
**Date:** April 17, 2026
**Status:** Draft v2.0 — Reference Implementation Available (164 tests passing)
**Repository:** github.com/openautonomyx/autonomyx-agent-identity

---

## Abstract

As AI agents become autonomous participants in software systems — making API calls, accessing databases, spending money, and acting on behalf of humans — the question of *who is this agent?* becomes as critical as *who is this user?*

Existing identity standards serve humans (OIDC/SAML) and services (OAuth 2.0 Client Credentials) well, but lack constructs for the unique characteristics of AI agents: dynamic creation, ephemeral lifecycle, human sponsorship, per-agent billing, and model-level access control.

This document proposes an **Agent Identity Model** — a set of normative attributes, lifecycle rules, and authorization patterns that define an AI agent as a first-class identity principal. It is accompanied by a **Reference Architecture** demonstrating one implementation using open-source components. The model is designed to be implementable on any identity infrastructure; the reference architecture is an example, not a requirement.

---

## 1. The Problem

### 1.1 Current Identity Landscape

| Principal Type | Established Standards | Maturity |
|---|---|---|
| Human users | OIDC, OAuth 2.0, SAML, FIDO2 | Mature (15+ years) |
| Service accounts | OAuth 2.0 Client Credentials, mTLS | Mature (10+ years) |
| AI Agents | Emerging (no consensus standard) | Early |

### 1.2 Why Existing Standards Are Insufficient for Agents

OAuth 2.0 Client Credentials models agents as "applications" — static, long-lived, administratively provisioned. However, AI agents exhibit characteristics that diverge from traditional service accounts:

- **Dynamic creation** — agents are often created programmatically at runtime by end users, not registered by administrators during deployment
- **Ephemeral lifecycle** — some agents exist for minutes or hours, not months or years
- **Accountable sponsorship** — agents act on behalf of a human or organizational sponsor who bears responsibility for the agent's actions
- **Scoped resource access** — agents require fine-grained access control at the model, tool, and data level
- **Auditable lineage** — every agent action must be traceable to both the agent identity and its accountable sponsor

Existing identity systems (Keycloak service accounts, Auth0 M2M tokens, AWS IAM roles) can be adapted to store agent metadata, but they lack native constructs for sponsorship, blueprints, ephemeral lifecycle management, and model-level authorization.

### 1.3 Related Work

**Microsoft Entra Agent ID** (GA 2025) introduced agents as a distinct principal type within the Azure ecosystem, with sponsor relationships, blueprint patterns, and a three-role admin model. This work validated the need for agent-specific identity. However, the implementation is proprietary to Microsoft Graph API and Azure Active Directory.

**Agent Auth Protocol** (Better Auth) defines how agents authenticate to services — the transport and handshake layer. It does not define what an agent IS as an identity entity, nor how agents are created, managed, or governed.

**AuthZEN** (OpenID Foundation) standardizes PDP↔PEP communication — how authorization questions are asked and answered. It is a transport protocol for authorization decisions, not an identity model.

These efforts are **complementary, not competing**. This document addresses the identity model layer that sits between human identity standards and agent communication protocols.

---

## 2. The Agent Identity Model

### 2.1 Design Principles

1. **Agents are a distinct principal type** — not users, not service accounts, not tokens with extra claims
2. **Accountable sponsorship** — every agent MUST have an accountable sponsor principal (typically a human, but MAY be an organizational entity or another agent with a human ultimately in the chain)
3. **Least-privilege by default** — agents start with zero access; all resource access is explicitly granted
4. **Ephemeral lifecycle is first-class** — agent creation and expiry are normal operations, not edge cases
5. **Billing is intrinsic** — per-agent cost attribution is part of the identity model
6. **Implementation-agnostic** — the model is defined in terms of abstract attributes and operations; specific technologies are implementation choices

### 2.2 Principal Types

An identity platform implementing this model MUST support three distinct principal types:

| Principal | Description | Authentication | Provisioning |
|---|---|---|---|
| **Human** | End users, administrators, sponsors | OIDC, SAML, passwords, MFA | Self-registration or admin-created |
| **Agent** | AI agents with autonomous behavior | API key, token, or delegated credential | Created by authorized principal |
| **Service** | Backend services, infrastructure | Client credentials, mTLS | Admin-provisioned |

Implementations MAY use a single identity store for all types or separate stores optimized for each type's access patterns. The choice of store does not affect conformance.

### 2.3 Agent Identity Attributes (Normative)

An agent identity record MUST include the following required attributes and MAY include the optional attributes:

| Attribute | Type | Required | Semantics |
|---|---|---|---|
| `agent_id` | string (UUID recommended) | MUST | Globally unique, immutable, never reused after revocation |
| `agent_name` | string | MUST | Human-readable identifier, unique within tenant scope |
| `agent_type` | enum | MUST | Classification: see Section 2.4 |
| `sponsor_id` | string | MUST | Identifier of the accountable sponsor principal |
| `tenant_id` | string | MUST | Tenant isolation boundary |
| `allowed_resources` | string[] | MUST | Explicit resource allowlist (models, tools, APIs) |
| `status` | enum | MUST | Lifecycle state: see Section 4.1 |
| `created_at` | datetime (ISO 8601) | MUST | Immutable creation timestamp |
| `owner_ids` | string[] | OPTIONAL | Technical administrators who can modify agent configuration |
| `manager_id` | string | OPTIONAL | Organizational hierarchy manager |
| `blueprint_id` | string | OPTIONAL | Reference to the template from which this agent was created |
| `budget_limit` | number | OPTIONAL | Maximum spend per budget period in the tenant's billing currency |
| `rate_limit` | number | OPTIONAL | Maximum requests or tokens per time window |
| `expires_at` | datetime (ISO 8601) | CONDITIONAL | MUST be present for ephemeral agents; OPTIONAL for persistent agents |
| `last_active_at` | datetime | OPTIONAL | Timestamp of most recent activity |
| `metadata` | object | OPTIONAL | Extensible key-value attributes for implementation-specific data |

### 2.4 Agent Types

| Type | Description | Lifecycle | `expires_at` |
|---|---|---|---|
| `workflow` | Long-lived agent running automated processes | Persistent until suspended/revoked | OPTIONAL |
| `ephemeral` | Short-lived agent for one-time or bounded tasks | Auto-expires | MUST be set |
| `tool` | Agent exposing capabilities via tool protocol (e.g., MCP) | Persistent, capability-scoped | OPTIONAL |

Implementations MAY define additional agent types. Custom types MUST follow the same lifecycle rules as the closest standard type.

### 2.5 Sponsor Semantics

The `sponsor_id` field identifies the principal accountable for the agent's actions. This is the most important design decision in the model.

**Requirements:**
- Every agent MUST have a `sponsor_id` at creation time
- The sponsor chain MUST ultimately resolve to a human or organizational entity capable of bearing accountability
- If the sponsor principal is deactivated or suspended, all agents sponsored by that principal SHOULD be suspended (sponsor cascade)
- An agent MAY sponsor another agent, but there MUST be a human or organization at the root of the sponsorship chain (maximum depth is an implementation choice)

**Rationale:** In regulated environments, compliance teams must answer "who is responsible for this agent's actions?" The answer must always resolve to an accountable entity, not to another agent in an infinite chain.

---

## 3. Authorization Model

### 3.1 Two-Layer Authorization

This model recommends (but does not require) separating authorization into two complementary layers:

**Layer 1 — Relationship-based access control (WHO):**
Determines whether a principal has a specific relationship to a resource.
- "Does agent:X have `can_use` relation to model:Y?"
- "Is agent:X a `member` of tenant:Z?"
- "Is user:Y the `sponsor` of agent:X?"

**Layer 2 — Condition-based policy evaluation (CONDITIONS):**
Evaluates runtime conditions against live system state.
- "Is agent:X status == active?"
- "Is agent:X not expired?"
- "Has agent:X exceeded its budget_limit?"
- "Does this request comply with data residency requirements?"

Both layers MUST pass for a request to be authorized. Either layer MAY be implemented using any suitable technology.

### 3.2 Rationale for Separation

Relationship engines (e.g., Zanzibar-model systems) excel at fast, indexed relationship lookups but cannot evaluate dynamic runtime conditions. Policy engines (e.g., Rego-based systems) excel at complex conditional logic but are not optimized for graph traversal. The separation allows each layer to use the most appropriate technology.

Implementations that can evaluate both relationships and conditions in a single system (e.g., a custom policy engine with graph support) MAY use a single layer while maintaining the logical separation.

### 3.3 Relationship to AuthZEN

The authorization checks described above can be transported using the AuthZEN protocol (OpenID Foundation) for PDP↔PEP communication. This model defines WHAT is checked; AuthZEN defines HOW the check is communicated. The specifications are complementary.

---

## 4. Agent Lifecycle

### 4.1 Status Model

```
                 ┌─────────┐
    create ────▶│  active  │◀──── reactivate
                 └────┬────┘
                      │
              suspend │         rotate
                      │       (stays active)
                      ▼
                 ┌──────────┐
                 │ suspended │
                 └─────┬────┘
                       │
               revoke  │  (or revoke from active)
                       ▼
                 ┌──────────┐
                 │ revoked   │  ← terminal, irreversible
                 └──────────┘

                 ┌──────────┐
    TTL expire ─▶│ expired   │  ← terminal for ephemeral agents
                 └──────────┘
```

| Status | Description | Transitions allowed |
|---|---|---|
| `active` | Agent can authenticate and make requests | → suspended, → revoked |
| `suspended` | Agent cannot authenticate; identity preserved | → active (reactivate), → revoked |
| `revoked` | Permanently deactivated; record preserved for audit | Terminal — no transitions |
| `expired` | TTL-triggered deactivation for ephemeral agents | Terminal — no transitions |

### 4.2 Core Lifecycle Operations

Implementations MUST support these operations:

| Operation | Input | Side Effects |
|---|---|---|
| **Create** | Agent attributes + sponsor authorization | Store record, issue credential, create authorization tuples |
| **Suspend** | agent_id + authorization | Invalidate credential, set status=suspended |
| **Reactivate** | agent_id + authorization | Issue new credential, set status=active |
| **Rotate** | agent_id + authorization | Issue new credential, invalidate old, status unchanged |
| **Revoke** | agent_id + authorization | Invalidate credential, set status=revoked, preserve record |

### 4.3 Credential Lifecycle

- Credentials (API keys, tokens) are issued at creation and rotation
- Credentials SHOULD be shown to the caller exactly once at issuance
- Suspended agents' credentials MUST be invalidated
- Revoked agents' credentials MUST be permanently invalidated
- Credential rotation SHOULD be zero-downtime: issue new before invalidating old

### 4.4 Audit Requirements

All lifecycle events MUST be logged with:
- Event type, timestamp, agent_id, agent_name
- Actor (who triggered the event) and actor type (human/system/agent)
- Tenant context
- Result (success/failure)

Audit records MUST be immutable — append-only, never modified or deleted.

---

## 5. SCIM 2.0 Integration

Implementations SHOULD expose a SCIM 2.0 (RFC 7644) endpoint to enable provisioning and deprovisioning from external identity providers (Okta, Azure AD, Google Workspace, JumpCloud, etc.).

### 5.1 SCIM User Mapping

Agent identities map to SCIM User resources with an extension schema:

```json
{
  "schemas": [
    "urn:ietf:params:scim:schemas:core:2.0:User",
    "urn:ietf:params:scim:schemas:extension:agentidentity:2.0:User"
  ],
  "userName": "fraud-sentinel",
  "active": true,
  "urn:ietf:params:scim:schemas:extension:agentidentity:2.0:User": {
    "entityType": "agent",
    "agentType": "workflow",
    "sponsorId": "admin@company.com",
    "tenantId": "tenant-acme"
  }
}
```

### 5.2 SCIM Operations

| SCIM Operation | Agent Lifecycle Mapping |
|---|---|
| POST /Users | Create agent |
| PATCH active=false | Suspend agent |
| PATCH active=true | Reactivate agent |
| DELETE /Users/{id} | Revoke agent |
| GET /Users | List agents + humans |
| GET /Groups | List tenants |

---

## 6. Discovery

Implementations SHOULD expose an agent configuration document at a well-known URL:

```
GET /.well-known/agent-configuration
```

The document SHOULD include:
- Platform name and version
- Supported agent types
- Available models/resources
- Registration endpoint
- Lifecycle endpoints
- Authorization model description
- Compliance certifications

This aligns with the emerging Agent Auth Protocol's discovery mechanism.

---

## 7. Conformance Profiles

### 7.1 Minimal Profile

For platforms with < 50 agents and basic access control needs:

- MUST implement: agent registry with all REQUIRED attributes
- MUST implement: create, suspend, revoke operations
- MUST implement: credential issuance and invalidation
- MAY use a single authorization layer

### 7.2 Enterprise Profile

For multi-tenant platforms with compliance requirements:

- MUST implement: all Minimal Profile requirements
- MUST implement: two-layer authorization (relationship + condition)
- MUST implement: audit logging with immutable storage
- MUST implement: sponsor cascade (sponsor deactivation → agent suspension)
- MUST implement: blueprint/template system
- SHOULD implement: SCIM 2.0 provisioning
- SHOULD implement: ephemeral agent auto-expiry

### 7.3 Regulated Profile

For platforms subject to GDPR, DPDP Act, SOC 2, or similar:

- MUST implement: all Enterprise Profile requirements
- MUST implement: data residency policy enforcement
- MUST implement: per-agent audit trail with sponsor attribution
- MUST implement: agent inventory with owner/sponsor accountability
- MUST implement: credential rotation policy (maximum age)
- SHOULD implement: integration with external compliance monitoring

---

## 8. Comparison to Related Work

| Capability | Entra Agent ID | OAuth 2.0 CC | Agent Auth Protocol | AuthZEN | **This Model** |
|---|---|---|---|---|---|
| Agent as distinct principal | ✅ | ❌ | Partially | ❌ | ✅ |
| Implementation-neutral | ❌ (Azure) | ✅ (RFC) | ✅ | ✅ | ✅ |
| Sponsor accountability | ✅ | ❌ | ❌ | ❌ | ✅ |
| Blueprint/template | ✅ | ❌ | ❌ | ❌ | ✅ |
| Ephemeral lifecycle | ✅ | ❌ | ❌ | ❌ | ✅ |
| Per-agent billing | ❌ | ❌ | ❌ | ❌ | ✅ |
| Resource-level access | Limited | Scopes | ❌ | ❌ | ✅ |
| Auth transport | Azure AD | RFC 6749 | ✅ (defines) | ✅ (defines) | Delegates to these |
| Conformance profiles | ❌ | ❌ | ❌ | ❌ | ✅ |
| SCIM provisioning | Via Entra | ❌ | ❌ | ❌ | ✅ |

**Note:** This model intentionally delegates authentication transport to existing standards (OAuth 2.0, Agent Auth Protocol) and authorization transport to AuthZEN. It focuses on the identity model layer — what an agent IS, not how it authenticates or how authorization decisions are communicated.

---

## 9. Reference Architecture

The following describes ONE implementation of this model using open-source components. **These technology choices are examples, not requirements for conformance.**

### 9.1 Component Mapping

| Model Layer | Reference Implementation | Alternatives |
|---|---|---|
| Human identity | Keycloak 25.0 (Apache 2.0) | Auth0, Okta, Entra ID, Logto, Authelia |
| Agent registry | SurrealDB v2.3.6 | PostgreSQL+JSONB, MongoDB, DynamoDB, CockroachDB |
| Relationship auth | OpenFGA v1.8.0 (Apache 2.0, CNCF) | SpiceDB, Ory Keto, Authzed, Cedar |
| Condition policy | OPA 0.70.0 (Apache 2.0, CNCF) | Cedar (AWS), Cerbos, Casbin |
| API gateway | APISIX (Apache 2.0) | Kong, Envoy, Traefik |
| LLM gateway | LiteLLM (MIT) | Custom, MLflow Gateway |
| Audit sink | VictoriaLogs (Apache 2.0) | Elasticsearch, Loki, ClickHouse |
| Secret management | OpenBao (MPL 2.0) | HashiCorp Vault, SOPS |
| Provisioning | SCIM 2.0 server (RFC 7644) | Custom REST API |

### 9.2 Reference Implementation Statistics

| Metric | Value |
|---|---|
| API endpoints | 41 |
| Modules | 14 |
| Unit tests | 150 |
| Integration tests (Testcontainers) | 14 |
| Total tests passing | 164 |
| SCIM 2.0 endpoints | 9 |
| MCP skill integrations | 41 |
| Docker registry images | 54 |

**Repository:** github.com/openautonomyx/autonomyx-agent-identity

### 9.3 Deployed Endpoints

| Service | URL |
|---|---|
| Agent Identity API | https://id.unboxd.cloud |
| API Gateway (26 routes) | https://api.unboxd.cloud |
| Interactive API Docs | https://id.unboxd.cloud/docs |
| OpenAPI Spec | https://id.unboxd.cloud/openapi.json |

---

## 10. Adoption Guide

### 10.1 Minimal Implementation (2-4 weeks)

1. Create an agent registry table/collection with the REQUIRED attributes from Section 2.3
2. Implement the five core lifecycle operations from Section 4.2
3. Issue and validate API keys or tokens as agent credentials
4. Add basic authorization: check `status == active` and `tenant_id` matches on every request

### 10.2 Migration from Service Accounts

For platforms currently modeling agents as OAuth client credentials:

1. Create agent registry with REQUIRED attributes
2. For each existing service account used as an agent: create a corresponding agent record, set `sponsor_id` to the responsible human
3. Set `allowed_resources` based on the resources the agent actually uses
4. Redirect authentication from client credentials to agent credentials
5. Enable policy checks in audit-only mode first, then enforce

### 10.3 Integration Patterns

**Greenfield:** Start with the reference implementation or implement the model from scratch on your preferred stack.

**Brownfield:** Keep existing human identity provider. Add agent registry alongside it. Wire authorization to check both human AND agent identities.

**Enterprise:** Full implementation with audit trail, compliance policies, SCIM provisioning, and multi-tenant isolation.

### 10.4 Compliance Considerations

This model provides architectural primitives that support compliance requirements. However, compliance depends on the COMPLETE system — including implementation quality, operational practices, and organizational policies. The model alone does not guarantee compliance with any regulation.

| Regulation | Relevant Model Features |
|---|---|
| GDPR (Records of Processing) | Sponsor attribution, audit trail |
| DPDP Act 2023 (India) | Condition-based data residency policy |
| SOC 2 (Access Control) | Relationship-based least-privilege access |
| ISO 27001 (Asset Management) | Agent registry as AI asset inventory |
| NIST AI RMF (Governance) | Blueprint pattern for approved agent templates |
| EU AI Act (Transparency) | Discovery document for agent capabilities |

### 10.5 When This Model Is Not Needed

- Simple chatbots with a single model and no multi-tenancy
- Internal tools with trusted users only — OAuth client credentials suffices
- Prototypes and experiments — skip identity, iterate on product first
- Fewer than 5 agents with manual key management

This model provides value when you have multiple agents with different access levels, multi-tenant deployments, compliance requirements, per-agent billing needs, or agents created dynamically by end users.

---

## 11. Future Work

1. **Formal token claims** — define standard JWT/token claims for agent identity attributes
2. **AuthZEN integration** — adopt OpenID AuthZEN as the authorization transport layer
3. **Agent-to-agent delegation** — formalize scoped delegation using transitive relationships
4. **Interoperability testing** — cross-implementation conformance test suite
5. **Verifiable credentials** — W3C VCs for portable agent identity across platforms
6. **IETF Internet-Draft** — submit for standards track consideration

---

## 12. License

This document is published under **Creative Commons Attribution 4.0 International (CC BY 4.0)**.

The reference implementation is published under the repository's open-source license.

**OpenAutonomyx (OPC) Private Limited**
No. 78/9, Outer Ring Road, Varthur Hobli, Bellandur, Bangalore South, Bangalore – 560103, Karnataka, India
CIN: U62010KA2026OPC215666
