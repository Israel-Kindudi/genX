import type { Metadata } from "next";
import AuthPage from "@/components/AuthPage";
import { Suspense } from "react";

export const metadata: Metadata = {
  title: "Create an account",
  robots: {
    index: false,
    follow: false,
  },
};


export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center text-slate-400">Loading…</div>}>
      <AuthPage initialMode="register" />
    </Suspense>
  );
}