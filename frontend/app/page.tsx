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
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/signup" className="rounded-md bg-accent px-4 py-2 font-medium">Start free workspace</Link>
              <Link href="/login" className="rounded-md border border-border px-4 py-2">Log in</Link>
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
          <h2 className="text-xl font-medium">End-to-end operator flow</h2>
          <ol className="mt-3 grid gap-3 text-sm text-slate-300 md:grid-cols-2">
            <li className="rounded-lg border border-border bg-slate-950/60 px-3 py-2">1. Sign up an organization and verify identity providers.</li>
            <li className="rounded-lg border border-border bg-slate-950/60 px-3 py-2">2. Log in and configure environment, policy baseline, and approval flows.</li>
            <li className="rounded-lg border border-border bg-slate-950/60 px-3 py-2">3. Operate agents in the console with alerts, audit, and revoke controls.</li>
            <li className="rounded-lg border border-border bg-slate-950/60 px-3 py-2">4. Manage spend and compliance from billing and policy governance pages.</li>
          </ol>
        </section>
      </main>
    </div>
  );
}
