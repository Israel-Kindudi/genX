"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Check, Shield, Zap, AlertTriangle } from "lucide-react";
import { usePlans, useMySubscription, type Plan } from "@/lib/usePlans";
import { isAuthenticated, getToken, decodeToken } from "@/lib/auth";
import CheckoutForm from "@/components/CheckoutForm";

export default function CheckoutPage() {
  const router = useRouter();
  const params = useParams();
  const search = useSearchParams();

  const planCode = String(params?.planCode ?? "");
  const cycle = (search.get("cycle") as "monthly" | "yearly") || "monthly";

  const { plans, isLoading } = usePlans({ publicOnly: true });
  const { sub } = useMySubscription();

  const plan: Plan | undefined = plans.find((p) => p.code === planCode);

  // Use null as "not yet checked" to avoid premature bounce
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    // Small delay so token write from AuthPage completes before we check
    const timer = setTimeout(() => {
      const authNow = isAuthenticated();
      setAuthed(authNow);

      const token = getToken();
      if (token) {
        const payload = decodeToken(token);
        setEmail((payload?.sub as string) || "");
      }
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  // Redirect only if we've confirmed the user is NOT authenticated
  useEffect(() => {
    if (authed === false) {
      const next = `/checkout/${planCode}?cycle=${cycle}`;
      router.replace(`/login?next=${encodeURIComponent(next)}`);
    }
  }, [authed, planCode, cycle, router]);

  if (isLoading || authed === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0B0F17] text-slate-500">
        Loading…
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#0B0F17]">
        <AlertTriangle className="h-8 w-8 text-amber-400" />
        <div className="text-slate-300">Plan &quot;{planCode}&quot; not found</div>
        <Link href="/#pricing" className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-slate-600">
          Back to pricing
        </Link>
      </div>
    );
  }

  if (done) {
    return <SuccessScreen plan={plan} />;
  }

  const price = cycle === "yearly" ? plan.price_yearly : plan.price_monthly;
  const suffix = cycle === "yearly" ? "/yr" : "/mo";

  return (
    <div className="min-h-screen bg-[#0B0F17] py-12">
      <div className="mx-auto max-w-5xl px-6">
        <Link href="/#pricing" className="mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200">
          <ArrowLeft className="h-4 w-4" /> Back to pricing
        </Link>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-5">
          <div className="lg:col-span-3">
            <div className="rounded-2xl border border-slate-800 bg-[#111723] p-6">
              <h1 className="mb-1 text-2xl font-semibold text-slate-100">Checkout</h1>
              <p className="mb-6 text-sm text-slate-400">
                Complete your subscription to <b>{plan.name}</b>.
              </p>

              <CheckoutForm
                planCode={plan.code}
                cycle={cycle}
                email={email}
                onSuccess={() => setDone(true)}
              />
            </div>

            <div className="mt-4 flex items-center justify-center gap-2 text-xs text-slate-500">
              <Shield className="h-3.5 w-3.5" /> 256-bit TLS · PCI-DSS via Stripe & Flutterwave
            </div>
          </div>

          <div className="lg:col-span-2">
            <div className="sticky top-6 rounded-2xl border border-slate-800 bg-[#111723] p-6">
              <h2 className="mb-4 text-sm font-medium uppercase tracking-wide text-slate-400">Order summary</h2>

              <div className="mb-4 flex items-start justify-between">
                <div>
                  <div className="text-lg font-semibold text-slate-100">{plan.name}</div>
                  <div className="text-xs text-slate-500">Billed {cycle === "yearly" ? "yearly" : "monthly"}</div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-semibold text-slate-100">${price.toLocaleString()}</div>
                  <div className="text-xs text-slate-500">{suffix}</div>
                </div>
              </div>

              <div className="mb-4 flex items-center gap-2 text-xs text-slate-400">
                <Zap className="h-3.5 w-3.5 text-emerald-400" />
                {plan.max_cycles.toLocaleString()} cycles ·{" "}
                {plan.cycles_expire ? "30-day expiry" : "never expire"}
              </div>

              <div className="my-4 h-px bg-slate-800" />

              <ul className="space-y-2">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-xs text-slate-300">
                    <Check className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-emerald-400" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>

              <div className="my-4 h-px bg-slate-800" />

              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Total due today</span>
                <span className="text-lg font-semibold text-slate-100">
                  ${price.toLocaleString()} {plan.currency}
                </span>
              </div>

              {sub?.plan && sub.plan.code !== plan.code && (
                <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-300">
                  You are switching from <b>{sub.plan.name}</b>. Your existing subscription will be canceled and replaced immediately.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SuccessScreen({ plan }: { plan: Plan }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#0B0F17] px-6">
      <div className="w-full max-w-md rounded-2xl border border-emerald-500/40 bg-emerald-500/5 p-8 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/15">
          <Check className="h-7 w-7 text-emerald-400" />
        </div>
        <h1 className="mb-2 text-2xl font-semibold text-slate-100">You&apos;re on {plan.name}</h1>
        <p className="mb-6 text-sm text-slate-400">Your subscription is active. Cycle limits apply instantly.</p>
        <div className="flex flex-col gap-2">
          <Link href="/dashboard" className="rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-slate-900 hover:bg-emerald-400">
            Go to dashboard
          </Link>
          <Link href="/dashboard/billing" className="rounded-lg border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:border-slate-600">
            View billing
          </Link>
        </div>
      </div>
    </div>
  );
}