import Link from "next/link";
import { TopNav } from "@/components/marketing/TopNav";

export default function HomePage() {
  return (
    <div>
      <TopNav />
      <main className="page-shell space-y-12">
        <section className="grid gap-8 md:grid-cols-2">
          <div>
            <p className="mb-2 text-sm uppercase tracking-[0.16em] text-slate-400">Agent Identity Plane</p>
            <h1 className="text-4xl font-semibold leading-tight">Govern identity, trust, and authorization across autonomous agents.</h1>
            <p className="mt-4 text-slate-300">AutonomyX gives platform teams one control plane for onboarding, authorizing, monitoring, and revoking AI agents across environments.</p>
            <div className="mt-6 flex gap-3">
              <Link href="/console" className="rounded-md bg-accent px-4 py-2 font-medium">Launch console</Link>
              <Link href="/developers" className="rounded-md border border-border px-4 py-2">Read docs</Link>
            </div>
          </div>
          <div className="card space-y-3">
            <h2 className="text-lg font-medium">Why agent identity now</h2>
            <ul className="list-disc space-y-2 pl-4 text-slate-300">
              <li>Agents are non-human workloads with privileged access.</li>
              <li>Static API keys and ad hoc ACLs fail multi-tenant governance.</li>
              <li>Security teams need auditability, policy controls, and lifecycle revocation.</li>
            </ul>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          {[
            ["Identity lifecycle", "Register, approve, expire, and revoke agent credentials with policy gates."],
            ["Policy enforcement", "Combine OpenFGA relationships with OPA policy decisions in one request path."],
            ["Discovery & catalog", "Expose trusted capability metadata for approved agents."]
          ].map(([title, body]) => (
            <article key={title} className="card">
              <h3 className="font-medium">{title}</h3>
              <p className="mt-2 text-sm text-slate-300">{body}</p>
            </article>
          ))}
        </section>

        <section className="card">
          <h2 className="text-xl font-medium">Architecture and integrations</h2>
          <p className="mt-2 text-slate-300">Identity API, policy engine, authorization graph, webhooks, and audit streams integrate with OpenFGA, OPA, Keycloak, APISIX, and SIEM tools.</p>
        </section>
      </main>
    </div>
  );
}
