import type { Metadata } from "next";
import { Suspense } from "react";
import AuthPage from "@/components/AuthPage";

export const metadata: Metadata = {
  title: "Sign in",
  robots: {
    index: false,
    follow: false,
  },
};


export default function LoginPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center text-slate-400">Loading…</div>}>
      <AuthPage initialMode="login" />
    </Suspense>
  );
}
