# Console Pages

## Complete now
- Dashboard metrics and dependency health cards.
- Agent list with status chips and detail drill-down.
- Agent detail with lifecycle action placeholders and audit timeline.

## Implemented as high-fidelity placeholders
- Registrations, discovery, policies, audit, webhooks, blueprints, integrations, settings, health.
- Each page lists concrete controls expected in production and maps to backend domain modules.

## Mock vs real
- All console data is mocked via `frontend/lib/site-data.ts` in this iteration.
- No authenticated session or backend API client is wired yet.
