import { PageHeader } from "@/components/console/PageHeader";

const invoices = [
  ["INV-2026-0042", "Apr 2026", "$4,920", "Paid"],
  ["INV-2026-0035", "Mar 2026", "$4,480", "Paid"],
  ["INV-2026-0028", "Feb 2026", "$4,020", "Paid"]
] as const;

export default function BillingPage() {
  return (
    <div>
      <PageHeader title="Billing" subtitle="Manage plan, usage, and payment controls for your agent identity environment." />
      <section className="grid gap-4 lg:grid-cols-3">
        <article className="card lg:col-span-2">
          <h2 className="text-lg font-medium">Current plan</h2>
          <p className="mt-1 text-sm text-slate-300">Enterprise · Annual contract · 2,500 active agent identities included</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-border bg-slate-950/60 p-3">
              <p className="text-xs uppercase text-slate-400">MTD usage</p>
              <p className="mt-1 text-xl font-semibold">1,942 agents</p>
            </div>
            <div className="rounded-lg border border-border bg-slate-950/60 p-3">
              <p className="text-xs uppercase text-slate-400">Overage</p>
              <p className="mt-1 text-xl font-semibold">$0</p>
            </div>
            <div className="rounded-lg border border-border bg-slate-950/60 p-3">
              <p className="text-xs uppercase text-slate-400">Renewal</p>
              <p className="mt-1 text-xl font-semibold">Jan 31, 2027</p>
            </div>
          </div>
          <button type="button" className="mt-4 rounded-md border border-border px-4 py-2 text-sm hover:border-slate-500">Contact account team</button>
        </article>

        <article className="card">
          <h2 className="text-lg font-medium">Payment method</h2>
          <p className="mt-2 text-sm text-slate-300">Visa •••• 4242</p>
          <p className="text-sm text-slate-300">Billing email: finance@acme.io</p>
          <button type="button" className="mt-4 w-full rounded-md bg-accent px-4 py-2 text-sm font-medium">Update payment details</button>
        </article>
      </section>

      <section className="mt-6 card">
        <h2 className="text-lg font-medium">Invoice history</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-slate-400">
              <tr>
                <th className="px-2 py-2">Invoice</th>
                <th className="px-2 py-2">Period</th>
                <th className="px-2 py-2">Amount</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map(([id, period, amount, status]) => (
                <tr key={id} className="border-t border-border">
                  <td className="px-2 py-2">{id}</td>
                  <td className="px-2 py-2">{period}</td>
                  <td className="px-2 py-2">{amount}</td>
                  <td className="px-2 py-2">{status}</td>
                  <td className="px-2 py-2"><button type="button" className="text-accent hover:underline">Download PDF</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
