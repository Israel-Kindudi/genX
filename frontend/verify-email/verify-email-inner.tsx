"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { saveToken } from "@/lib/auth";

export default function VerifyEmailInner() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token");

  const [state, setState] = useState<"loading" | "ok" | "error">("loading");
  const [message, setMessage] = useState("Verifying your email…");

  useEffect(() => {
    if (!token) {
      setState("error");
      setMessage("Missing verification token.");
      return;
    }

    (async () => {
      try {
        const res = await api.post("/api/auth/verify-email", { token });
        
        // Save the fresh JWT immediately so they are logged in
        saveToken(res.data.access_token);
        
        setState("ok");
        setMessage(res.data.message || "Email verified");
        
        // Give the user a beat to see the success, then redirect to billing
        setTimeout(() => router.push("/dashboard/billing"), 1500);
      } catch (e: any) {
        setState("error");
        setMessage(
          e?.response?.data?.detail ??
          "Verification failed. The link may have expired."
        );
      }
    })();
  }, [token, router]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#0a0d14] px-6">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#111625] p-8 text-center shadow-2xl">
        {state === "loading" && (
          <>
            <Loader2 className="mx-auto mb-4 h-10 w-10 animate-spin text-cyan-400" />
            <h1 className="mb-2 text-xl font-semibold text-slate-100">Verifying…</h1>
            <p className="text-sm text-slate-400">{message}</p>
          </>
        )}

        {state === "ok" && (
          <>
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/15">
              <CheckCircle2 className="h-7 w-7 text-emerald-400" />
            </div>
            <h1 className="mb-2 text-xl font-semibold text-slate-100">
              Email verified!
            </h1>
            <p className="mb-4 text-sm text-slate-400">
              Redirecting you to your billing dashboard…
            </p>
          </>
        )}

        {state === "error" && (
          <>
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-red-500/15">
              <AlertTriangle className="h-7 w-7 text-red-400" />
            </div>
            <h1 className="mb-2 text-xl font-semibold text-slate-100">
              Verification failed
            </h1>
            <p className="mb-6 text-sm text-slate-400">{message}</p>
            <button
              onClick={() => router.push("/login")}
              className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-cyan-400 transition-colors"
            >
              Back to login
            </button>
          </>
        )}
      </div>
    </div>
  );
}