"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CreditCard, Download, AlertTriangle, CheckCircle2 } from "lucide-react";
import { useMySubscription, useInvoices, cancelSubscription } from "@/lib/usePlans";
import UsageMeter from "@/components/UsageMeter";

export default function BillingPage() {
  const router = useRouter();
  const { sub, mutate } = useMySubscription();
  const { invoices, mutate: mutateInvoices } = useInvoices();

  const [toast, setToast] = useState<{ kind: "ok" | "err"; msg: string } | null>(
    null
  );

  const currentCode = sub?.plan?.code ?? "trial";
  const plan = sub?.plan;
  const usage = sub?.usage ?? {
    live_sessions: 0,
    backtests: 0,
    mining_runs: 0,
    optimizations: 0,
  };
  const subs = sub?.subscription;
  const cancelling = subs?.cancel_at_period_end;

  const onCancel = async () => {
    if (!confirm("Cancel at the end of the current period?")) return;
    try {
      await cancelSubscription();
      await Promise.all([mutate(), mutateInvoices()]);
      setToast({ kind: "ok", msg: "Subscription will cancel at period end" });
    } catch {
      setToast({ kind: "err", msg: "Failed to cancel" });
    } finally {
      setTimeout(() => setToast(null), 3500);
    }
  };

  return (
    <div className="space-y-8 p-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-100">Billing & Plan</h1>
        <p className="text-sm text-slate-400">
          Manage your GenX subscription, usage, and invoices.
        </p>
      </header>

      {/* current plan summary */}
      <section className="rounded-xl border border-slate-800 bg-[#111723] p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-300">
              <CreditCard className="h-6 w-6" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-500">
                Current plan
              </div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-semibold text-slate-100">
                  {plan?.name ?? "Trial"}
                </span>
                {subs && (
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${statusColor(
                      subs.status
                    )}`}
                  >
                    {subs.status}
                  </span>
                )}
              </div>
              {subs?.current_period_end && (
                <div className="mt-1 text-xs text-slate-400">
                  {cancelling
                    ? `Cancels on ${fmtDate(subs.current_period_end)}`
                    : `Renews ${fmtDate(subs.current_period_end)}`}
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {subs && !cancelling && currentCode !== "trial" && (
              <button
                onClick={onCancel}
                className="rounded-lg border border-red-500/40 px-4 py-2 text-sm text-red-300 hover:bg-red-500/10"
              >
                Cancel at period end
              </button>
            )}
            <button
              onClick={() => router.push("/dashboard/billing/plans")}
              className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-emerald-400"
            >
              {currentCode === "trial" ? "Upgrade plan" : "Change plan"}
            </button>
          </div>
        </div>
        {cancelling && (
          <div className="mt-4 flex items-center gap-2 text-sm text-amber-400">
            <AlertTriangle className="h-4 w-4" /> Cancels at end of period
          </div>
        )}
      </section>

      {/* usage */}
      <section>
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-slate-400">
          Usage this month
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <UsageMeter
            label="Live sessions"
            used={usage.live_sessions}
            cap={plan?.max_live_sessions ?? 1}
          />
          <UsageMeter
            label="Backtests"
            used={usage.backtests}
            cap={plan?.max_backtests_per_day ?? 50}
          />
          <UsageMeter
            label="Mining runs"
            used={usage.mining_runs}
            cap={plan?.max_mining_runs ?? 0}
          />
          <UsageMeter
            label="Optimizations"
            used={usage.optimizations}
            cap={999}
          />
        </div>
      </section>

      {/* invoices */}
      <section>
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-slate-400">
          Billing history
        </h2>
        <div className="overflow-hidden rounded-xl border border-slate-800 bg-[#111723]">
          {invoices.length === 0 ? (
            <div className="p-6 text-center text-sm text-slate-500">
              No invoices yet. They&apos;ll appear here after your first paid plan
              change.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-[#0B0F17] text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 text-left">Date</th>
                  <th className="px-4 py-3 text-left">Description</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-right">Amount</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr key={inv.id} className="border-t border-slate-800/70">
                    <td className="px-4 py-3 text-slate-300">
                      {fmtDate(inv.issued_at)}
                    </td>
                    <td className="px-4 py-3 text-slate-200">
                      {inv.description}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs ${invStatusColor(
                          inv.status
                        )}`}
                      >
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-200">
                      ${inv.amount.toFixed(2)} {inv.currency}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => alert("Invoice PDF download — stub")}
                        className="inline-flex items-center gap-1 rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:border-slate-600"
                      >
                        <Download className="h-3 w-3" /> PDF
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

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

function fmtDate(d: string | Date) {
  return new Date(d).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function statusColor(s: string) {
  switch (s) {
    case "active":
      return "bg-emerald-500/15 text-emerald-300";
    case "trialing":
      return "bg-emerald-500/15 text-emerald-300";
    case "past_due":
      return "bg-amber-500/15 text-amber-300";
    case "canceled":
      return "bg-red-500/15 text-red-300";
    default:
      return "bg-slate-700/40 text-slate-300";
  }
}

function invStatusColor(s: string) {
  switch (s) {
    case "paid":
      return "bg-emerald-500/15 text-emerald-300";
    case "pending":
      return "bg-amber-500/15 text-amber-300";
    case "failed":
      return "bg-red-500/15 text-red-300";
    case "refunded":
      return "bg-slate-700/40 text-slate-300";
    default:
      return "bg-slate-700/40 text-slate-300";
  }
}