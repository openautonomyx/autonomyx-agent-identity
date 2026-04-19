import Link from "next/link";
import { SideNav } from "@/components/console/SideNav";

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen lg:flex">
      <SideNav />
      <main className="flex-1 p-6">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-panel px-4 py-3 text-sm">
          <p className="text-slate-300">Signed in as <span className="font-medium text-slate-100">ops@acme.io</span> · Tenant <span className="font-medium text-slate-100">acme-prod</span></p>
          <div className="flex items-center gap-3">
            <Link href="/console/billing" className="text-slate-300 hover:text-white">Billing</Link>
            <Link href="/login" className="text-slate-300 hover:text-white">Sign out</Link>
          </div>
        </div>
        {children}
      </main>
    </div>
  );
}
