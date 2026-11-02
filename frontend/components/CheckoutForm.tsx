"use client";

import { useState } from "react";
import { CreditCard, Smartphone, Lock, AlertTriangle } from "lucide-react";
import {
  CheckoutPayload,
  PaymentMethod,
  validateCheckout,
  submitCheckout,
} from "@/lib/useCheckout";

interface Props {
  planCode: string;
  cycle: "monthly" | "yearly";
  email: string;
  onSuccess: () => void;
}

const MOBILE_PROVIDERS = [
  { code: "MPESA", label: "M-Pesa" },
  { code: "MTN", label: "MTN MoMo" },
  { code: "ORANGE", label: "Orange Money" },
  { code: "AIRTEL", label: "Airtel Money" },
];

export default function CheckoutForm({ planCode, cycle, email, onSuccess }: Props) {
  const [method, setMethod] = useState<PaymentMethod>("card");
  const [phone, setPhone] = useState("");
  const [country, setCountry] = useState("KE");
  const [momoProvider, setMomoProvider] = useState("MPESA");
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [globalError, setGlobalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    setGlobalError(null);

    const payload: CheckoutPayload = {
      plan_code: planCode,
      billing_cycle: cycle,
      payment_method: method,
      provider: method === "card" ? "stripe" : "flutterwave",
      email,
      ...(method === "mobile_money" && {
        phone_number: phone,
        country_code: country,
        mobile_money_provider: momoProvider,
      }),
    };

    const v = validateCheckout(payload);
    if (Object.keys(v).length > 0) {
      setErrors(v);
      return;
    }

    setBusy(true);
    const res = await submitCheckout(payload);
    setBusy(false);

    if (!res.ok) {
      setGlobalError(res.error ?? "Checkout failed");
      return;
    }

    if (res.checkout_url) {
      window.location.href = res.checkout_url;
    } else {
      onSuccess();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => setMethod("card")}
          className={`flex items-center justify-center gap-2 rounded-lg border px-3 py-3 text-sm font-medium transition ${
            method === "card"
              ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
              : "border-slate-700 bg-[#0B0F17] text-slate-400 hover:border-slate-600"
          }`}
        >
          <CreditCard className="h-4 w-4" /> Card
        </button>
        <button
          type="button"
          onClick={() => setMethod("mobile_money")}
          className={`flex items-center justify-center gap-2 rounded-lg border px-3 py-3 text-sm font-medium transition ${
            method === "mobile_money"
              ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
              : "border-slate-700 bg-[#0B0F17] text-slate-400 hover:border-slate-600"
          }`}
        >
          <Smartphone className="h-4 w-4" /> Mobile Money
        </button>
      </div>

      {method === "card" ? (
        <div className="rounded-lg border border-slate-700 bg-[#0B0F17] px-4 py-4 text-sm text-slate-400">
          You will be redirected to <span className="text-slate-200">Stripe</span> to securely
          enter your Visa or Mastercard details.
        </div>
      ) : (
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs uppercase tracking-wide text-slate-500">
              Provider
            </label>
            <select
              value={momoProvider}
              onChange={(e) => setMomoProvider(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-[#0B0F17] px-3 py-2.5 text-sm text-slate-100 focus:border-emerald-500 focus:outline-none"
            >
              {MOBILE_PROVIDERS.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <Field label="Country" value={country} onChange={setCountry} placeholder="KE, NG, GH, TZ, ZA" error={errors.country_code} />
          <Field label="Phone number" value={phone} onChange={setPhone} placeholder="+254 712 345 678" type="tel" error={errors.phone_number} />

          <p className="text-xs text-slate-500">
            You will receive a prompt on your phone to authorize the payment.
          </p>
        </div>
      )}

      {globalError && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          <AlertTriangle className="h-4 w-4" /> {globalError}
        </div>
      )}

      <button
        type="submit"
        disabled={busy}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-500 px-4 py-3 text-sm font-semibold text-slate-900 transition hover:bg-emerald-400 disabled:opacity-60"
      >
        {busy ? "Redirecting…" : <><Lock className="h-4 w-4" /> Continue to payment</>}
      </button>

      <p className="text-center text-xs text-slate-500">
        Secured by Stripe & Flutterwave. No card details are stored on our servers.
      </p>
    </form>
  );
}

function Field({
  label, value, onChange, error, placeholder, type = "text", inputMode,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
  placeholder?: string;
  type?: string;
  inputMode?: "text" | "numeric" | "email" | "tel";
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs uppercase tracking-wide text-slate-500">{label}</label>
      <div className={`flex items-center gap-2 rounded-lg border bg-[#0B0F17] px-3 py-2.5 transition ${error ? "border-red-500/60" : "border-slate-700 focus-within:border-emerald-500"}`}>
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          inputMode={inputMode}
          className="w-full bg-transparent text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none"
        />
      </div>
      {error && <div className="mt-1 text-xs text-red-400">{error}</div>}
    </div>
  );
}