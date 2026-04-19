import Link from "next/link";
import { consoleNav } from "@/lib/site-data";

export function SideNav() {
  return (
    <aside className="hidden w-64 flex-col border-r border-border bg-panel p-4 lg:flex">
      <div className="mb-5 text-sm font-semibold">Agent Identity Console</div>
      <nav className="space-y-1 text-sm">
        {consoleNav.map(([label, href]) => (
          <Link key={href} href={href} className="block rounded-md px-3 py-2 text-slate-300 hover:bg-slate-900 hover:text-white">{label}</Link>
        ))}
      </nav>
    </aside>
  );
}
