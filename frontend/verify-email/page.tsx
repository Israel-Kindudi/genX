"use client";

import { Suspense } from "react";
import VerifyEmailInner from "./verify-email-inner";
import { Loader2 } from "lucide-react";

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-[#0a0d14] text-slate-500">
          <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
        </div>
      }
    >
      <VerifyEmailInner />
    </Suspense>
  );
}