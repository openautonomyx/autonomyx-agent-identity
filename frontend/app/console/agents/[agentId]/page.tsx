import { PageHeader } from "@/components/console/PageHeader";
import { agents } from "@/lib/site-data";
import { Badge } from "@/components/ui/Badge";

export default function AgentDetailPage({ params }: { params: { agentId: string } }) {
  const agent = agents.find((item) => item.id === params.agentId) ?? agents[0];
  return (
    <div>
      <PageHeader title={agent.name} subtitle="Identity detail, policy relationships, and lifecycle actions." />
      <section className="grid gap-4 md:grid-cols-2">
        <article className="card space-y-2">
          <h2 className="font-medium">Summary</h2>
          <p>ID: {agent.id}</p>
          <p>Status: <Badge tone={agent.status === "active" ? "success" : "warn"}>{agent.status}</Badge></p>
          <p>Owner: {agent.owner}</p>
          <p>Capabilities: {agent.capabilities.join(", ")}</p>
        </article>
        <article className="card">
          <h2 className="font-medium">Actions</h2>
          <div className="mt-3 flex gap-2 text-sm">
            <button className="rounded-md border border-border px-3 py-2">Suspend</button>
            <button className="rounded-md border border-border px-3 py-2">Reactivate</button>
            <button className="rounded-md bg-rose-600 px-3 py-2">Revoke</button>
          </div>
        </article>
      </section>
      <section className="mt-4 card">
        <h2 className="font-medium">Audit timeline</h2>
        <ul className="mt-2 space-y-2 text-sm text-slate-300">
          <li>2026-04-19T08:22Z · authz.check.allow · correlation=2d10...</li>
          <li>2026-04-18T11:10Z · policy.assignment.updated · correlation=76ac...</li>
          <li>2026-04-15T13:50Z · identity.rotate_credentials · correlation=90ba...</li>
        </ul>
      </section>
    </div>
  );
}
