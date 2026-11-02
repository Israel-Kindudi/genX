"use client";

import { useRouter } from "next/navigation";

export function usePlanRedirect() {
  const router = useRouter();

  const handlePlanSelect = (planCode: string, cycle: "monthly" | "yearly" = "monthly") => {
    // 1. Free trial or custom contact doesn't need this
    if (planCode === "trial") {
      router.push("/login?next=/dashboard");
      return;
    }
    if (planCode === "firm_xl") {
      window.location.href = "mailto:sales@genx.trade?subject=GenX%20Firm%20XL";
      return;
    }

    // 2. Check if the user is logged in
    const token = 
      typeof window !== "undefined" 
        ? localStorage.getItem("genx_token") || sessionStorage.getItem("genx_token")
        : null;

    if (token) {
      // Logged in: go straight to checkout
      router.push(`/checkout/${planCode}?cycle=${cycle}`);
    } else {
      // Not logged in: save intent, then go to login
      localStorage.setItem("pending_plan", planCode);
      localStorage.setItem("pending_cycle", cycle);
      router.push("/login?redirect=checkout");
    }
  };

  return { handlePlanSelect };
}