import { PageHeader } from "@/components/console/PageHeader";

export function PlaceholderPage({ title, subtitle, items }: { title: string; subtitle: string; items: string[] }) {
  return (
    <div>
      <PageHeader title={title} subtitle={subtitle} />
      <section className="grid gap-3 md:grid-cols-2">
        {items.map((item) => (
          <article key={item} className="card text-sm text-slate-200">{item}</article>
        ))}
      </section>
    </div>
  );
}
