import Link from "next/link";
import { TopNav } from "@/components/marketing/TopNav";

const onboardingFlow = [
  ["Organization", "Create workspace, choose region, and verify domain ownership."],
  ["Admin access", "Invite initial security and platform operators with least-privilege roles."],
  ["First integration", "Connect IdP, secret store, and webhook destination for lifecycle events."],
  ["Policy baseline", "Apply default OPA and OpenFGA templates before production agent registration."]
] as const;

export default function SignupPage() {
  return (
    <div>
      <TopNav />
      <main className="page-shell grid gap-8 lg:grid-cols-[1.2fr_1fr]">
        <section className="card">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Get started</p>
          <h1 className="mt-2 text-3xl font-semibold">Create your AutonomyX workspace</h1>
          <p className="mt-3 text-sm text-slate-300">Launch with a guided setup that takes your team from first sign-up to production-safe agent identity controls.</p>

          <form className="mt-6 grid gap-4 md:grid-cols-2" aria-label="Signup form">
            <label className="text-sm md:col-span-1">
              <span className="mb-1 block text-slate-300">First name</span>
              <input type="text" className="w-full rounded-md border border-border bg-slate-950 px-3 py-2" />
            </label>
            <label className="text-sm md:col-span-1">
              <span className="mb-1 block text-slate-300">Last name</span>
              <input type="text" className="w-full rounded-md border border-border bg-slate-950 px-3 py-2" />
            </label>
            <label className="text-sm md:col-span-2">
              <span className="mb-1 block text-slate-300">Work email</span>
              <input type="email" className="w-full rounded-md border border-border bg-slate-950 px-3 py-2" />
            </label>
            <label className="text-sm md:col-span-2">
              <span className="mb-1 block text-slate-300">Company name</span>
              <input type="text" className="w-full rounded-md border border-border bg-slate-950 px-3 py-2" />
            </label>
            <button type="button" className="rounded-md bg-accent px-4 py-2.5 text-sm font-medium text-white md:col-span-2">Start onboarding</button>
          </form>

          <p className="mt-4 text-xs text-slate-400">
            By continuing, you agree to the service terms and security policy review process.
          </p>
          <p className="mt-2 text-sm text-slate-300">
            Already have an account? <Link href="/login" className="text-accent hover:underline">Sign in</Link>
          </p>
        </section>

        <aside className="card">
          <h2 className="text-lg font-medium">Onboarding flow</h2>
          <ol className="mt-4 space-y-3 text-sm text-slate-300">
            {onboardingFlow.map(([step, description], index) => (
              <li key={step} className="rounded-lg border border-border bg-slate-950/60 px-3 py-2">
                <p className="font-medium text-slate-100">{index + 1}. {step}</p>
                <p className="mt-1">{description}</p>
              </li>
            ))}
          </ol>
        </aside>
      </main>
    </div>
  );
}
