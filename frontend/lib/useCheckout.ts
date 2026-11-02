import { api } from "./api";

export type PaymentMethod = "card" | "mobile_money";

export interface CheckoutPayload {
  plan_code: string;
  billing_cycle: "monthly" | "yearly";
  payment_method: PaymentMethod;
  provider: "stripe" | "flutterwave";
  email: string;
  phone_number?: string;
  country_code?: string;
  mobile_money_provider?: string;
}

export interface CheckoutResult {
  ok: boolean;
  error?: string;
  checkout_url?: string;
}

export async function submitCheckout(payload: CheckoutPayload): Promise<CheckoutResult> {
  try {
    const res = await api.post("/api/payments/checkout", payload);
    return { ok: true, checkout_url: res.data.checkout_url };
  } catch (err: any) {
    return {
      ok: false,
      error: err.response?.data?.detail || err.message || "Checkout failed",
    };
  }
}

export function validateCheckout(payload: CheckoutPayload): Record<string, string> {
  const errors: Record<string, string> = {};

  if (!payload.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.email)) {
    errors.email = "Valid email required";
  }

  if (payload.payment_method === "mobile_money") {
    if (!payload.phone_number) {
      errors.phone_number = "Phone number required";
    } else if (!/^\+?\d{8,15}$/.test(payload.phone_number.replace(/\s/g, ""))) {
      errors.phone_number = "Invalid phone number";
    }
    if (!payload.country_code) {
      errors.country_code = "Country required";
    }
  }

  return errors;
}