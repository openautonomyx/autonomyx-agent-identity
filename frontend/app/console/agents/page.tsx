import Link from "next/link";
import { PageHeader } from "@/components/console/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { agents } from "@/lib/site-data";

export default function AgentsPage() {
  return (
    <div>
      <PageHeader title="Agents" subtitle="Searchable and filterable catalog of all managed agent identities." />
      <div className="card overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-slate-400">
            <tr>
              <th className="py-2">Name</th><th>Type</th><th>Status</th><th>Owner</th><th>Tenant</th><th>Last seen</th><th>Expiry</th><th />
            </tr>
          </thead>
          <tbody>
            {agents.map((agent) => (
              <tr key={agent.id} className="border-t border-border">
                <td className="py-3">{agent.name}</td>
                <td>{agent.type}</td>
                <td><Badge tone={agent.status === "active" ? "success" : "warn"}>{agent.status}</Badge></td>
                <td>{agent.owner}</td>
                <td>{agent.tenant}</td>
                <td>{agent.lastSeen}</td>
                <td>{agent.expiry}</td>
                <td><Link className="text-accent" href={`/console/agents/${agent.id}`}>View</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
