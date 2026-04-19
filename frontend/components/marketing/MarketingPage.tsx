import { TopNav } from "@/components/marketing/TopNav";

export function MarketingPage({ title, subtitle, bullets }: { title: string; subtitle: string; bullets: string[] }) {
  return (
    <div>
      <TopNav />
      <main className="page-shell">
        <h1 className="text-3xl font-semibold">{title}</h1>
        <p className="mt-3 max-w-3xl text-slate-300">{subtitle}</p>
        <div className="mt-6 grid gap-3 md:grid-cols-2">
          {bullets.map((item) => (
            <div key={item} className="card text-sm text-slate-200">{item}</div>
          ))}
        </div>
      </main>
    </div>
  );
}
