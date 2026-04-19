import { PageHeader } from "@/components/console/PageHeader";
import { Badge } from "@/components/ui/Badge";

const policies = [
  ["tenant-boundary-allow", "v12", "OPA", "Active"],
  ["agent-expiry-block", "v7", "OPA", "Active"],
  ["fga-owner-write", "v4", "OpenFGA", "Draft"]
] as const;

export default function PoliciesPage() {
  return (
    <div>
      <PageHeader title="Policy Console" subtitle="Author, test, and roll out OPA + OpenFGA policy controls with explicit review flow." />

      <section className="grid gap-4 lg:grid-cols-[1.1fr_1fr]">
        <article className="card">
          <h2 className="text-lg font-medium">Add policy</h2>
          <p className="mt-1 text-sm text-slate-300">Create a draft policy, scope it to tenant or environment, and send for security approval.</p>

          <form className="mt-4 grid gap-3" aria-label="Add policy form">
            <label className="text-sm">
              <span className="mb-1 block text-slate-300">Policy name</span>
              <input type="text" placeholder="eg. deny-untrusted-endpoint" className="w-full rounded-md border border-border bg-slate-950 px-3 py-2" />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-slate-300">Engine</span>
              <select className="w-full rounded-md border border-border bg-slate-950 px-3 py-2">
                <option>OPA</option>
                <option>OpenFGA</option>
              </select>
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-slate-300">Scope</span>
              <input type="text" placeholder="acme-prod / payments" className="w-full rounded-md border border-border bg-slate-950 px-3 py-2" />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-slate-300">Policy logic</span>
              <textarea rows={6} className="w-full rounded-md border border-border bg-slate-950 px-3 py-2" placeholder="allow := input.agent.trust_level == \"verified\"" />
            </label>
            <div className="flex flex-wrap gap-2">
              <button type="button" className="rounded-md bg-accent px-4 py-2 text-sm font-medium">Save draft</button>
              <button type="button" className="rounded-md border border-border px-4 py-2 text-sm hover:border-slate-500">Run simulation</button>
              <button type="button" className="rounded-md border border-border px-4 py-2 text-sm hover:border-slate-500">Submit for approval</button>
            </div>
          </form>
        </article>

        <article className="card">
          <h2 className="text-lg font-medium">Release flow</h2>
          <ol className="mt-3 space-y-3 text-sm text-slate-300">
            <li className="rounded-lg border border-border bg-slate-950/60 px-3 py-2"><span className="font-medium text-slate-100">1. Draft</span> · Create policy and attach change ticket.</li>
            <li className="rounded-lg border border-border bg-slate-950/60 px-3 py-2"><span className="font-medium text-slate-100">2. Simulate</span> · Run against last 24h authorization decisions.</li>
            <li className="rounded-lg border border-border bg-slate-950/60 px-3 py-2"><span className="font-medium text-slate-100">3. Approve</span> · Require 2 reviewers for production scopes.</li>
            <li className="rounded-lg border border-border bg-slate-950/60 px-3 py-2"><span className="font-medium text-slate-100">4. Enforce</span> · Roll out with staged deny thresholds.</li>
          </ol>
        </article>
      </section>

      <section className="mt-6 card">
        <h2 className="text-lg font-medium">Policy catalog</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-slate-400">
              <tr>
                <th className="px-2 py-2">Name</th>
                <th className="px-2 py-2">Revision</th>
                <th className="px-2 py-2">Engine</th>
                <th className="px-2 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {policies.map(([name, revision, engine, status]) => (
                <tr key={name} className="border-t border-border">
                  <td className="px-2 py-2">{name}</td>
                  <td className="px-2 py-2">{revision}</td>
                  <td className="px-2 py-2">{engine}</td>
                  <td className="px-2 py-2">
                    {status === "Active" ? <Badge tone="success">{status}</Badge> : <Badge tone="warn">{status}</Badge>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
