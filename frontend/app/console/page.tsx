import { PageHeader } from "@/components/console/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { dashboardStats } from "@/lib/site-data";

export default function DashboardPage() {
  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Runtime view of identity lifecycle, policy posture, and dependencies." />
      <section className="grid gap-3 md:grid-cols-3">
        {dashboardStats.map(([label, value]) => (
          <article key={label} className="card">
            <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
            <p className="kpi mt-2">{value}</p>
          </article>
        ))}
      </section>
      <section className="mt-6 grid gap-4 md:grid-cols-2">
        <article className="card">
          <h2 className="mb-3 font-medium">Dependency health</h2>
          <div className="space-y-2 text-sm">
            <p>Postgres: <Badge tone="success">Healthy</Badge></p>
            <p>OpenFGA: <Badge tone="success">Healthy</Badge></p>
            <p>OPA: <Badge tone="warn">Degraded latency</Badge></p>
            <p>Gateway: <Badge tone="success">Healthy</Badge></p>
          </div>
        </article>
        <article className="card">
          <h2 className="mb-3 font-medium">Recent denials</h2>
          <ul className="space-y-2 text-sm text-slate-300">
            <li>policy.deny · agt-ops-compliance-02 · missing tenancy scope</li>
            <li>policy.deny · agt-lab-scraper-12 · revoked credential</li>
            <li>policy.deny · agt-prod-risk-11 · endpoint trust mismatch</li>
          </ul>
        </article>
      </section>
    </div>
  );
}
