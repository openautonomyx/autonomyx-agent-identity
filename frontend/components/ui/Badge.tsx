import { ReactNode } from "react";

export function Badge({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "success" | "warn" | "danger" }) {
  const toneClass = {
    default: "bg-slate-800 text-slate-200",
    success: "bg-emerald-500/20 text-emerald-300",
    warn: "bg-amber-500/20 text-amber-300",
    danger: "bg-rose-500/20 text-rose-300"
  }[tone];
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${toneClass}`}>{children}</span>;
}
