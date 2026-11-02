"use client";

import { useState } from "react";
import { Check, Sparkles, Building2, Star, Zap } from "lucide-react";
import { getPlanDescription, usePlans, type Plan } from "@/lib/usePlans";
import BillingCycleToggle from "./BillingCycleToggle";
import { usePlanRedirect } from "@/lib/authRedirect"; // NEW IMPORT

// ... (theme function stays exactly the same) ...
function theme(code: string) {
  switch (code) {
    case "trial": return { border: "border-slate-800", bg: "bg-[#0e1220]", accent: "text-slate-300", button: "border border-slate-700 text-slate-200 hover:border-slate-500", chip: null };
    case "starter": return { border: "border-emerald-500/25", bg: "bg-gradient-to-b from-emerald-500/[0.04] to-transparent", accent: "text-emerald-300", button: "border border-emerald-500/50 text-emerald-200 hover:bg-emerald-500/10", chip: null };
    case "pro": return { border: "border-emerald-500/50", bg: "bg-gradient-to-b from-emerald-500/[0.07] to-transparent", accent: "text-emerald-300", button: "bg-emerald-500 text-slate-900 hover:bg-emerald-400", chip: { label: "Most popular", cls: "bg-emerald-500 text-slate-900", icon: Star } };
    case "firm": return { border: "border-violet-500/40", bg: "bg-gradient-to-b from-violet-500/[0.06] to-transparent", accent: "text-violet-300", button: "border border-violet-500/60 text-violet-200 hover:bg-violet-500/10", chip: { label: "For desks", cls: "bg-violet-500 text-slate-900", icon: Sparkles } };
    case "firm_xl": return { border: "border-amber-500/50", bg: "bg-gradient-to-b from-amber-500/[0.07] to-transparent", accent: "text-amber-300", button: "bg-amber-500 text-slate-900 hover:bg-amber-400", chip: { label: "For prop firms", cls: "bg-amber-500 text-slate-900", icon: Building2 } };
    default: return { border: "border-slate-800", bg: "bg-[#111723]", accent: "text-slate-300", button: "border border-slate-700 text-slate-200 hover:border-slate-600", chip: null };
  }
}

function PricingCard({ plan, cycle }: { plan: Plan; cycle: "monthly" | "yearly" }) {
  const t = theme(plan.code);
  const { handlePlanSelect } = usePlanRedirect(); // NEW HOOK
  
  const isFree = plan.code === "trial" || plan.price_monthly === 0;
  const yearlyTotal = Math.round(plan.price_monthly * 12 * 0.83);
  const price = cycle === "yearly" ? Math.round(yearlyTotal / 12) : plan.price_monthly;
  
  const cycleCount = ({
    trial: 500,
    starter: cycle === "yearly" ? 46080 : 3840,
    pro: cycle === "yearly" ? 115200 : 9600,
    firm: cycle === "yearly" ? 230400 : 19200,
    firm_xl: cycle === "yearly" ? 368640 : 30720,
  } as Record<string, number | undefined>)[plan.code] ?? plan.max_cycles;
  
  const expiryDays = cycle === "yearly" ? 365 : 30;
  
  const equityFeature = ({
    trial: "Minimum deposit $50",
    starter: "Equity range $100 – $5,000 (per account)",
    pro: "Equity range $6,000 – $50,000 (per account)",
    firm: "Unlimited account equity",
  } as Record<string, string | undefined>)[plan.code];
  
  const visibleFeatures = plan.features.filter(
    (feature) => !/\bcycles?\b|\bequity\b/i.test(feature)
  );

  const ctaLabel = plan.code === "trial" ? "Start free" : plan.code === "firm_xl" ? "Contact sales" : "Get started";

  return (
    <div className={`pricing-card relative flex h-full flex-col rounded-2xl border p-6 ${t.border} ${t.bg} ${plan.code === "pro" ? "pricing-card--featured shadow-[0_0_40px_-12px_rgba(6,182,212,0.45)]" : ""}`}>
      {t.chip && (
        <div className={`absolute -top-3 left-6 inline-flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wide ${t.chip.cls}`}>
          <t.chip.icon className="h-3 w-3" /> {t.chip.label}
        </div>
      )}

      <div>
        <div className={`text-sm font-semibold uppercase tracking-wider ${t.accent}`}>{plan.name}</div>
        <div className="mt-1 min-h-[2.5rem] text-sm text-slate-400">{getPlanDescription(plan)}</div>
      </div>

      <div className="mt-4 min-h-[4.5rem]">
        <div className="flex items-baseline gap-1">
          <span className="text-4xl font-bold text-slate-100">{isFree ? "$0" : `$${price.toLocaleString()}`}</span>
          {!isFree && <span className="text-sm text-slate-500">/mo</span>}
          {isFree && <span className="text-sm text-slate-500">forever</span>}
        </div>
        <div className="min-h-5 text-xs text-slate-500">
          {cycle === "yearly" && !isFree ? `$${yearlyTotal.toLocaleString()} billed yearly` : "\u00a0"}
        </div>
      </div>

      {cycleCount != null && (
        <div className="-mt-1 flex items-baseline gap-1.5 text-xs text-slate-500">
          <Zap className={`relative top-[2px] h-3.5 w-3.5 shrink-0 ${t.accent}`} />
          <span className={`font-semibold ${t.accent}`}>{cycleCount.toLocaleString()}</span>
          <span>cycles{isFree ? "" : ` · ${expiryDays}-day expiry`}</span>
        </div>
      )}

      <div className="my-5 h-px w-full bg-slate-800" />

      <ul className="flex-1 space-y-2.5">
        {[
          isFree ? "500 cycles (one-time)" : `${cycleCount?.toLocaleString()} cycles (${expiryDays}-day expiry)`,
          ...visibleFeatures,
          ...(equityFeature ? [equityFeature] : []),
        ].map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-slate-300">
            <Check className={`mt-0.5 h-4 w-4 flex-shrink-0 ${t.accent}`} />
            <span>{f}</span>
          </li>
        ))}
      </ul>

      {/* CHANGED: Button instead of Link */}
      <button
        onClick={() => handlePlanSelect(plan.code, cycle)}
        className={`pricing-cta mt-6 block w-full rounded-lg px-4 py-2.5 text-center text-sm font-semibold transition ${t.button}`}
      >
        <span className="relative z-10">{ctaLabel}</span>
      </button>
    </div>
  );
}

export default function PricingSection() {
  const [cycle, setCycle] = useState<"monthly" | "yearly">("monthly");
  const { plans, isLoading } = usePlans({ publicOnly: true });

  return (
    <section id="pricing" className="pricing-section relative py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mb-12 text-center">
          <div className="mb-3 text-xs font-semibold uppercase tracking-widest text-emerald-400">Pricing</div>
          <h2 className="text-4xl font-bold text-slate-100 md:text-5xl">Choose your <span className="gradient-text">research engine</span></h2>
          <p className="mx-auto mt-4 max-w-2xl text-slate-400">Cycles are the currency of GenX. Every live trading iteration consumes one. Pick the plan that matches your scale.</p>
          <div className="mt-6 flex justify-center">
            <BillingCycleToggle cycle={cycle} onChange={setCycle} />
          </div>
        </div>

        {isLoading ? (
          <div className="text-center text-slate-500">Loading plans…</div>
        ) : (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {plans.map((p) => (
              <PricingCard key={p.code} plan={p} cycle={cycle} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}