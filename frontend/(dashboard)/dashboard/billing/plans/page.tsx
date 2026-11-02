"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, AlertTriangle } from "lucide-react";
import { usePlans, useMySubscription, changePlan } from "@/lib/usePlans";
import PlanCard from "@/components/PlanCard";
import BillingCycleToggle from "@/components/BillingCycleToggle";

export default function ChoosePlanPage() {
  const router = useRouter();
  const { plans, isLoading } = usePlans();
  const { sub, mutate } = useMySubscription();

  const [cycle, setCycle] = useState<"monthly" | "yearly">("monthly");
  const [busy, setBusy] = useState<string | null>(null);
  const [confirmCode, setConfirmCode] = useState<string | null>(null);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; msg: string } | null>(
    null
  );

  const currentCode = sub?.plan?.code ?? "trial";

  const pick = (code: string) => {
    if (code === currentCode) return;
    // enterprise plan → contact sales
    if (code === "firm_xl") {
      window.location.href = "mailto:sales@genx.trade?subject=GenX%20Firm%20XL";
      return;
    }
    setConfirmCode(code);
  };

  const confirm = async () => {
    if (!confirmCode) return;
    const code = confirmCode;
    setBusy(code);
    try {
      await changePlan(code, cycle);
      await mutate();
      setToast({ kind: "ok", msg: `You're now on ${code.toUpperCase()}` });
      setTimeout(() => router.push("/dashboard/billing"), 900);
    } catch (e: any) {
      setToast({
        kind: "err",
        msg: e?.response?.data?.detail ?? "Failed to change plan",
      });
      setTimeout(() => setToast(null), 3500);
    } finally {
      setBusy(null);
      setConfirmCode(null);
    }
  };

  const confirmingPlan = plans.find((p) => p.code === confirmCode);
  const confirmingPrice = confirmingPlan
    ? cycle === "yearly"
      ? confirmingPlan.price_yearly
      : confirmingPlan.price_monthly
    : 0;

  return (
    <div className="space-y-8 p-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/dashboard/billing")}
            className="rounded-lg border border-slate-700 p-2 text-slate-400 hover:border-slate-600 hover:text-slate-200"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <h1 className="text-2xl font-semibold text-slate-100">
              Choose your plan
            </h1>
            <p className="text-sm text-slate-400">
              Upgrade, downgrade, or switch billing cycle at any time.
            </p>
          </div>
        </div>
        <BillingCycleToggle cycle={cycle} onChange={setCycle} />
      </header>

      {isLoading ? (
        <div className="text-slate-500">Loading plans…</div>
      ) : (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {plans.map((p) => (
            <PlanCard
              key={p.code}
              plan={p}
              cycle={cycle}
              current={p.code === currentCode}
              onChoose={pick}
              busy={busy === p.code}
            />
          ))}
        </div>
      )}

      <section className="rounded-xl border border-slate-800 bg-[#111723] p-5">
        <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-slate-400">
          What happens when I switch?
        </h2>
        <ul className="space-y-1 text-sm text-slate-300">
          <li>
            • Your current subscription is canceled immediately and replaced by the
            new one.
          </li>
          <li>
            • A new billing period starts today (
            {cycle === "yearly" ? "12 months" : "30 days"}).
          </li>
          <li>
            • If the new plan costs money, an invoice appears on your billing page.
          </li>
          <li>
            • Cycle counts, symbol limits, and strategy limits apply instantly.
          </li>
        </ul>
      </section>

      {confirmCode && confirmingPlan && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/60"
            onClick={() => !busy && setConfirmCode(null)}
          />
          <div className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border border-slate-800 bg-[#111723] p-6 shadow-2xl">
            <h3 className="mb-2 text-lg font-semibold text-slate-100">
              Switch to {confirmingPlan.name}?
            </h3>
            <p className="mb-4 text-sm text-slate-400">
              You&apos;ll be billed{" "}
              <span className="text-slate-200">
                ${confirmingPrice.toFixed(2)} /{" "}
                {cycle === "yearly" ? "year" : "month"}
              </span>
              . Billing is stubbed for now — no real charge occurs.
            </p>
            <div className="flex justify-end gap-2">
              <button
                disabled={!!busy}
                onClick={() => setConfirmCode(null)}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-slate-600 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                disabled={!!busy}
                onClick={confirm}
                className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-emerald-400 disabled:opacity-50"
              >
                {busy ? "Processing…" : "Confirm switch"}
              </button>
            </div>
          </div>
        </>
      )}

      {toast && (
        <div
          className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-lg border px-4 py-3 text-sm shadow-2xl ${
            toast.kind === "ok"
              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
              : "border-red-500/40 bg-red-500/10 text-red-300"
          }`}
        >
          {toast.kind === "ok" ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <AlertTriangle className="h-4 w-4" />
          )}
          {toast.msg}
        </div>
      )}
    </div>
  );
}