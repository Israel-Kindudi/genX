"use client";
import { Plan } from "@/lib/usePlans";

const STYLES: Record<string, string> = {
  trial:   "bg-slate-700/40 text-slate-300 border-slate-600/50",
  starter: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  pro:     "bg-cyan-500/15 text-cyan-300 border-cyan-500/40",
  firm:    "bg-violet-500/15 text-violet-300 border-violet-500/40",
  firm_xl: "bg-amber-500/15 text-amber-300 border-amber-500/40",
};

export default function PlanBadge({ plan }: { plan?: Plan | null }) {
  const code = plan?.code ?? "trial";
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${STYLES[code] ?? STYLES.trial}`}>
      {plan?.name ?? "Trial"}
    </span>
  );
}