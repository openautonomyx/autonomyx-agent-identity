export const marketingNav = [
  ["Product", "/product"],
  ["Architecture", "/architecture"],
  ["Security", "/security"],
  ["Developers", "/developers"],
  ["Integrations", "/integrations"],
  ["Pricing", "/pricing"],
  ["Open Source", "/open-source"],
  ["Contact", "/contact"]
] as const;

export const consoleNav = [
  ["Dashboard", "/console"],
  ["Agents", "/console/agents"],
  ["Registrations", "/console/registrations"],
  ["Discovery", "/console/discovery"],
  ["Policies", "/console/policies"],
  ["Audit", "/console/audit"],
  ["Webhooks", "/console/webhooks"],
  ["Blueprints", "/console/blueprints"],
  ["Integrations", "/console/integrations"],
  ["Settings", "/console/settings"],
  ["System Health", "/console/health"]
] as const;

export const dashboardStats = [
  ["Total agents", "1,942"],
  ["Active", "1,641"],
  ["Suspended", "42"],
  ["Expired", "157"],
  ["Revoked", "102"],
  ["Policy denials (24h)", "31"]
] as const;

export const agents = [
  {
    id: "agt-prod-payments-01",
    name: "Payments Orchestrator",
    type: "service-agent",
    status: "active",
    owner: "finops@acme.io",
    tenant: "acme-prod",
    capabilities: ["payments.route", "risk.score"],
    lastSeen: "2026-04-19T08:22:00Z",
    expiry: "2026-08-01"
  },
  {
    id: "agt-ops-compliance-02",
    name: "Compliance Watcher",
    type: "governance-agent",
    status: "suspended",
    owner: "security@acme.io",
    tenant: "acme-prod",
    capabilities: ["audit.export", "policy.monitor"],
    lastSeen: "2026-04-19T06:14:00Z",
    expiry: "2026-05-01"
  }
] as const;
