import Link from "next/link";
import { marketingNav } from "@/lib/site-data";

export function TopNav() {
  return (
    <header className="border-b border-border bg-bg/90">
      <div className="page-shell flex items-center justify-between py-4">
        <Link href="/" className="text-lg font-semibold">AutonomyX Identity Plane</Link>
        <nav className="hidden gap-5 text-sm text-slate-300 md:flex">
          {marketingNav.map(([label, href]) => (
            <Link key={href} href={href} className="hover:text-white">{label}</Link>
          ))}
          <Link href="/console" className="rounded-md bg-accent px-3 py-1.5 font-medium text-white">Console</Link>
        </nav>
      </div>
    </header>
  );
}
