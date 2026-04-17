# Autonomyx Platform — Architecture Document
*Last updated: April 17, 2026*

## Infrastructure

### Server 1 — Primary VPS (96GB RAM, 24 CPU, 387GB disk)
**IP:** 51.75.251.56 | **Host:** vps.openautonomyx.com

| Service | URL | Port | Status |
|---|---|---|---|
| LiteLLM Gateway | https://llm.openautonomyx.com | 4000 | ✅ Running |
| Langflow | https://flows.openautonomyx.com | 7860 | ✅ Running |
| Grafana | https://metrics.openautonomyx.com | 3000 | ✅ Running |
| GlitchTip | https://errors.openautonomyx.com | 8080 | ✅ Running |
| Trust Centre | https://trust.openautonomyx.com | 8888 | ✅ Running |
| Dockge | https://dockge.openautonomyx.com | 5001 | ✅ Running |
| pgAdmin | https://db.openautonomyx.com | 5050 | ✅ Running |
| Coolify | https://vps.openautonomyx.com | 8000 | ✅ Running |
| Ollama | internal | 11434 | ✅ Running |
| Postgres | internal | 5432 | ✅ Healthy |
| OpenFGA | internal | 8080 | ✅ Running |
| OPA | internal | 8181 | ✅ Running |
| Prometheus | internal | 9090 | ✅ Running |
| OTEL Collector | internal | 4317/4318 | ✅ Running |
| Jaeger | internal | 16686 | ✅ Running |
| VictoriaLogs | internal | 9428 | ✅ Running |
| SurrealDB | internal | 8000 | ✅ Running |
| Playwright | internal | 8400 | ✅ Running |
| Classifier | internal | 8100 | ✅ Running |
| Infisical | internal | 8080 | ✅ Running |

### Server 2 — Secondary VPS (48GB RAM)
**IP:** 15.235.211.93 | **Host:** unboxd.cloud

| Service | URL | Port | Status |
|---|---|---|---|
| Agent Identity API | https://id.unboxd.cloud | 8500 | ✅ Running |
| Keycloak | https://auth.unboxd.cloud | 8180 | ✅ Running |
| AgentCode (OpenHands) | https://code.agnxxt.com | 3080 | ✅ Running |
| NocoDB | https://db.unboxd.cloud | 8091 | ✅ Running |
| OpenFGA (agents) | internal | 8080 | ✅ Running |
| OPA (agents) | internal | 8181 | ✅ Running |
| SurrealDB (agents) | internal | 8000 | ✅ Running |
| Keycloak DB | internal | 5432 | ✅ Running |

## Models (Ollama on Server 1)

| Model | Size | Task | Status |
|---|---|---|---|
| Qwen3-30B-A3B | 18GB | Reasoning, agent, chat | ✅ Pulled |
| Qwen2.5-Coder-32B | 19GB | Code | ✅ Pulled |

## Three Principal Types

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   HUMANS    │     │   AGENTS    │     │  SERVICES   │
│  Keycloak   │     │  SurrealDB  │     │  Keycloak   │
│  OIDC/JWT   │     │  Virtual Key│     │  Client Cred│
│  Browser    │     │  API call   │     │  M2M        │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────┬───────┘───────────────────┘
                   │
            ┌──────▼──────┐
            │   OpenFGA   │  WHO can access WHAT
            └──────┬──────┘
                   │
            ┌──────▼──────┐
            │     OPA     │  CONDITIONS (budget, DPDP, local-first)
            └──────┬──────┘
                   │
            ┌──────▼──────┐
            │   LiteLLM   │  Route to model
            └──────┬──────┘
                   │
            ┌──────▼──────┐
            │   Ollama    │  Serve response
            └─────────────┘
```

## Repositories

| Repo | Purpose |
|---|---|
| openautonomyx/autonomyx-model-gateway | Gateway + 25 services + CI/CD |
| openautonomyx/autonomyx-agent-identity | Agent Identity System (98 tests) |

## Key Decisions

| Decision | Choice | Why |
|---|---|---|
| Agent identity store | SurrealDB (not Keycloak) | Agents are first-class entities, not service accounts |
| Relationship auth | OpenFGA (CNCF) | Zanzibar model, vendor-neutral |
| Policy engine | OPA (CNCF Graduated) | Rego, vendor-neutral |
| Human auth | Keycloak | Enterprise SSO, SAML, OIDC |
| Orchestration | Temporal (planned) | Durable execution, MIT licensed |
| LLM inference | Ollama on CPU | Zero marginal cost, 96GB RAM |
| Tunnel | frp (disabled) | Apache 2.0, no vendor |
| Logs | VictoriaLogs | Apache 2.0, replaced Loki |
| Traces | Jaeger (CNCF) | Replaced Tempo |
| Cache | Valkey | Apache 2.0, replaced Redis |
