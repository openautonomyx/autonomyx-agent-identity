import Link from "next/link";
import { TopNav } from "@/components/marketing/TopNav";

const loginChecks = [
  "Step 1 · Enter workspace email and password.",
  "Step 2 · Complete MFA challenge (TOTP, passkey, or SSO assertion).",
  "Step 3 · Land in the console scoped to your assigned tenant and role."
];

export default function LoginPage() {
  return (
    <div>
      <TopNav />
      <main className="page-shell grid gap-8 lg:grid-cols-[1.2fr_1fr]">
        <section className="card">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Sign in</p>
          <h1 className="mt-2 text-3xl font-semibold">Log in to the AutonomyX console</h1>
          <p className="mt-3 text-sm text-slate-300">Use your operator account to manage agent onboarding, policy enforcement, and billing controls.</p>

          <form className="mt-6 space-y-4" aria-label="Login form">
            <label className="block text-sm">
              <span className="mb-1 block text-slate-300">Workspace email</span>
              <input type="email" placeholder="ops@your-company.com" className="w-full rounded-md border border-border bg-slate-950 px-3 py-2 text-sm outline-none ring-accent/50 focus:ring" />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-slate-300">Password</span>
              <input type="password" placeholder="••••••••" className="w-full rounded-md border border-border bg-slate-950 px-3 py-2 text-sm outline-none ring-accent/50 focus:ring" />
            </label>
            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 text-slate-300">
                <input type="checkbox" className="rounded border-border bg-slate-950" />
                Remember this device
              </label>
              <Link href="/contact" className="text-accent hover:underline">Forgot password?</Link>
            </div>
            <button type="button" className="w-full rounded-md bg-accent px-4 py-2.5 text-sm font-medium text-white">
              Continue to MFA
            </button>
          </form>

          <p className="mt-4 text-sm text-slate-300">
            New to AutonomyX?{" "}
            <Link href="/signup" className="text-accent hover:underline">Create your organization</Link>
          </p>
        </section>

        <aside className="card">
          <h2 className="text-lg font-medium">Secure login flow</h2>
          <ul className="mt-4 space-y-3 text-sm text-slate-300">
            {loginChecks.map((item) => (
              <li key={item} className="rounded-lg border border-border bg-slate-950/60 px-3 py-2">{item}</li>
            ))}
          </ul>
          <p className="mt-5 text-xs text-slate-400">Enterprise SSO with OIDC/SAML and SCIM provisioning is configured from Console → Integrations.</p>
        </aside>
      </main>
    </div>
  );
}
