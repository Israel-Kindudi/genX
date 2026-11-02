"use client";
import useSWR from "swr";
import { api } from "./api";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// ---------- types ----------
export interface Plan {
  id: number;
  code: string;
  name: string;
  description: string;

  price_monthly: number;
  price_yearly: number;
  currency: string;

  max_cycles: number;
  cycles_expire: boolean;
  trial_days?: number | null;

  max_mt5_accounts: number;
  max_symbols: number;
  max_strategies: number;
  all_symbols_visible: boolean;
  all_strategies_visible: boolean;

  max_account_equity: number;

  max_live_sessions: number;
  max_backtests_per_day: number;
  max_mining_runs: number;

  allow_ml_filter: boolean;
  allow_regime_detection: boolean;
  allow_api_access: boolean;
  allow_multi_terminal: boolean;

  support_response_hours: number;
  latency_tier: string;
  api_access: string;
  custom_risk_rails: boolean;
  early_access_symbols: boolean;
  signal_channel: boolean;
  custom_hub: boolean;
  white_label: boolean;
  dedicated_infrastructure: boolean;

  features: string[];
  sort_order: number;
}

export function getPlanDescription(plan: Pick<Plan, "code" | "description">) {
  switch (plan.code) {
    case "trial":
      return "Discover the platform.";
    case "starter":
      return "For individual traders looking to scale.";
    case "firm":
      return "For serious traders and small desks.";
    default:
      return plan.description;
  }
}

export interface Subscription {
  id: number;
  status: string;
  started_at: string;
  current_period_end?: string | null;
  cancel_at_period_end: boolean;
  plan?: Plan | null;
}

export interface Usage {
  live_sessions: number;
  backtests: number;
  mining_runs: number;
  optimizations: number;
}

export interface MySubscription {
  user_id: number;
  email: string;
  role: string;
  is_active: boolean;
  plan?: Plan | null;
  subscription?: Subscription | null;
  usage: Usage;
}

export interface Invoice {
  id: number;
  amount: number;
  currency: string;
  status: string;
  description: string;
  period_start?: string | null;
  period_end?: string | null;
  issued_at: string;
}

// ---------- public fetcher (no auth) ----------
const publicFetcher = (url: string) =>
  fetch(`${API_BASE}${url}`).then((r) => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  });

// ---------- authenticated fetcher ----------
const authFetcher = (url: string) => api.get(url).then((r) => r.data);

// ---------- hooks ----------
export function usePlans({ publicOnly = false }: { publicOnly?: boolean } = {}) {
  const url = publicOnly ? "/api/public/plans" : "/api/subscriptions/plans";
  const { data, error, isLoading, mutate } = useSWR<Plan[]>(
    url,
    publicOnly ? publicFetcher : authFetcher,
    { revalidateOnFocus: false }
  );
  return { plans: data ?? [], error, isLoading, mutate };
}

export function useMySubscription() {
  const { data, error, isLoading, mutate } = useSWR<MySubscription>(
    "/api/subscriptions/me",
    authFetcher,
    { revalidateOnFocus: true, refreshInterval: 60000 }
  );
  return { sub: data, error, isLoading, mutate };
}

export function useInvoices() {
  const { data, error, isLoading, mutate } = useSWR<Invoice[]>(
    "/api/subscriptions/invoices",
    authFetcher,
    { revalidateOnFocus: false }
  );
  return { invoices: data ?? [], error, isLoading, mutate };
}

export async function changePlan(plan_code: string, billing_cycle = "monthly") {
  const r = await api.post("/api/subscriptions/change", {
    plan_code,
    billing_cycle,
  });
  return r.data;
}

export async function cancelSubscription() {
  const r = await api.post("/api/subscriptions/cancel");
  return r.data;
}