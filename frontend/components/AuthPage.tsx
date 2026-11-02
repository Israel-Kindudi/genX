"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, ArrowUpRight, LockKeyhole, ShieldCheck, Zap } from "lucide-react";
import { api } from "@/lib/api";
import { saveToken } from "@/lib/auth";
import { getPasswordStrength } from "@/lib/passwordStrength";
import AuthBranding from "@/components/AuthBranding";
import { signIn } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";

type AuthMode = "login" | "register";
type AuthPageProps = { initialMode: AuthMode };

export default function AuthPage({ initialMode }: AuthPageProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mode, setMode] = useState<AuthMode>(initialMode);
  
  // Form fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [country, setCountry] = useState("");
  
  // UI state
  const [rememberInstance, setRememberInstance] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const rememberedEmail = localStorage.getItem("genx_remembered_email");
    if (rememberedEmail) {
      setEmail(rememberedEmail);
      setRememberInstance(true);
    }
  }, []);

  const passwordStrength = useMemo(() => getPasswordStrength(password), [password]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSuccessMsg("");
    setLoading(true);

    try {
      if (mode === "register") {
        // 1. Register User
        await api.post("/api/auth/register", {
          email,
          password,
          full_name: fullName,
          phone_number: phoneNumber,
          country: country,
          terms_accepted: acceptedTerms,
          terms_version: "v1.0"
        });

        // 2. Show success message
        setSuccessMsg("Account created! Please check your email to verify your account before logging in.");
        setLoading(false);
        return;
      }

      // --- Login Flow ---
      if (rememberInstance) {
        localStorage.setItem("genx_remembered_email", email);
      } else {
        localStorage.removeItem("genx_remembered_email");
      }

      const form = new URLSearchParams();
      form.append("username", email);
      form.append("password", password);

      const res = await api.post("/api/auth/token", form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      const token = res.data.access_token;
      if (!token) throw new Error("No access token returned");

      saveToken(token, rememberInstance);
      await new Promise((resolve) => setTimeout(resolve, 50));

      // --- NEW: Check for pending plan ---
      const pendingPlan = localStorage.getItem("pending_plan");
      const pendingCycle = localStorage.getItem("pending_cycle") || "monthly";
      
      if (pendingPlan) {
        localStorage.removeItem("pending_plan");
        localStorage.removeItem("pending_cycle");
        router.push(`/checkout/${pendingPlan}?cycle=${pendingCycle}`);
      } else {
        router.push("/dashboard");
      }

    } catch (err: any) {
      setError(
        err.response?.data?.detail || err.message || "Authentication failed"
      );
      setLoading(false);
    }
  }

  const handleGoogleLogin = async () => {
    // Check if they were trying to buy a plan
    const pendingPlan = localStorage.getItem("pending_plan");
    const pendingCycle = localStorage.getItem("pending_cycle") || "monthly";
    
    // Set the callback destination
    const callbackUrl = pendingPlan 
      ? `/checkout/${pendingPlan}?cycle=${pendingCycle}` 
      : "/dashboard";
      
    // If we're going to checkout, clear the intent so it doesn't linger
    if (pendingPlan) {
      localStorage.removeItem("pending_plan");
      localStorage.removeItem("pending_cycle");
    }

    // This calls NextAuth, which then hits our backend /api/auth/google-login
    await signIn("google", { callbackUrl });
  };

  return (
    <main className="flex min-h-[calc(100vh-5rem)] items-center justify-center px-4 py-12 sm:px-6 lg:py-16">
      <div className="grid w-full max-w-6xl overflow-hidden rounded-2xl border border-slate-800/80 bg-[#111723]/90 shadow-2xl shadow-black/30 backdrop-blur-xl lg:min-h-[660px] lg:grid-cols-[1.05fr_0.95fr]">
        
        {/* Left Side - Branding */}
        <section className="relative hidden overflow-hidden border-r border-slate-800/80 bg-[radial-gradient(ellipse_at_16%_8%,rgba(16,185,129,0.14),transparent_42%),linear-gradient(145deg,rgba(22,31,46,0.8),rgba(11,15,23,0.8))] p-10 lg:flex lg:flex-col lg:justify-between xl:p-14">
          <div className="pointer-events-none absolute inset-0 opacity-[0.14] [background-image:linear-gradient(rgba(148,163,184,0.2)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.2)_1px,transparent_1px)] [background-size:48px_48px]" />
          <div className="relative">
            <AuthBranding />
            <h2 className="mt-6 max-w-lg text-3xl font-semibold leading-tight text-slate-100 xl:text-4xl">
              Quantitative intelligence, engineered for global markets.
            </h2>
            <p className="mt-4 max-w-lg text-sm leading-7 text-slate-400">
              GenX models each market as a chromosome-like data structure, the
              Market DNA, and evolves strategy parameters with a genetic
              algorithm guided by statistical fitness.
            </p>
          </div>

          <div className="relative space-y-6">
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-xl border border-slate-800/80 bg-[#0B0F17]/60 p-4">
                <Activity className="h-4 w-4 text-emerald-400" />
                <div className="mt-3 font-mono text-lg text-slate-100">08</div>
                <div className="mt-1 text-[10px] uppercase tracking-wider text-slate-500">
                  DNA chromosomes
                </div>
              </div>
              <div className="rounded-xl border border-slate-800/80 bg-[#0B0F17]/60 p-4">
                <Zap className="h-4 w-4 text-emerald-400" />
                <div className="mt-3 font-mono text-lg text-slate-100">10+</div>
                <div className="mt-1 text-[10px] uppercase tracking-wider text-slate-500">
                  Strategies
                </div>
              </div>
              <div className="rounded-xl border border-slate-800/80 bg-[#0B0F17]/60 p-4">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                <div className="mt-3 font-mono text-lg text-slate-100">GA</div>
                <div className="mt-1 text-[10px] uppercase tracking-wider text-slate-500">
                  Optimisation
                </div>
              </div>
            </div>
            <blockquote className="border-l border-emerald-500/50 pl-4 text-sm leading-6 text-slate-300">
              “Markets are not random walks.”
              <footer className="mt-2 font-mono text-[10px] uppercase tracking-widest text-slate-500">
                GenX methodology
              </footer>
            </blockquote>
          </div>
        </section>

        {/* Right Side - Form */}
        <section className="flex items-center justify-center p-6 sm:p-10 xl:p-14">
          <div className="w-full max-w-md">
            <div className="mb-8 lg:hidden">
              <AuthBranding />
            </div>

            <div className="mb-8">
              <h1 className="text-3xl font-semibold tracking-tight text-slate-100">
                {mode === "login" ? "Welcome back" : "Create your account"}
              </h1>
              <p className="mt-2 text-sm text-slate-400">
                {mode === "login"
                  ? "Sign in to your GenX account."
                  : "We'll send you a verification link by email."}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              
              {/* Registration Fields */}
              {mode === "register" && (
                <>
                  <div>
                    <label htmlFor="full-name" className="mb-2 block text-xs font-medium text-slate-300">
                      Full legal name
                    </label>
                    <input
                      id="full-name"
                      type="text"
                      autoComplete="name"
                      placeholder="Your full name"
                      required
                      value={fullName}
                      onChange={(event) => setFullName(event.target.value)}
                      className="w-full rounded-lg border border-slate-800 bg-[#0B0F17] px-4 py-3 text-sm text-slate-100 placeholder:text-slate-600 focus:border-emerald-500 focus:outline-none"
                    />
                  </div>
                  
                  {/* Phone & Country */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="country" className="mb-2 block text-xs font-medium text-slate-300">
                        Country
                      </label>
                      <input
                        id="country"
                        type="text"
                        placeholder="e.g. Kenya"
                        required
                        value={country}
                        onChange={(event) => setCountry(event.target.value)}
                        className="w-full rounded-lg border border-slate-800 bg-[#0B0F17] px-4 py-3 text-sm text-slate-100 placeholder:text-slate-600 focus:border-emerald-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label htmlFor="phone" className="mb-2 block text-xs font-medium text-slate-300">
                        Phone Number
                      </label>
                      <input
                        id="phone"
                        type="tel"
                        placeholder="+254..."
                        required
                        value={phoneNumber}
                        onChange={(event) => setPhoneNumber(event.target.value)}
                        className="w-full rounded-lg border border-slate-800 bg-[#0B0F17] px-4 py-3 text-sm text-slate-100 placeholder:text-slate-600 focus:border-emerald-500 focus:outline-none"
                      />
                    </div>
                  </div>
                </>
              )}

              {/* Common Fields */}
              <div>
                <label htmlFor="email" className="mb-2 block text-xs font-medium text-slate-300">
                  Email address
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  placeholder="Email address"
                  aria-label="Email address"
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  className="w-full rounded-lg border border-slate-800 bg-[#0B0F17] px-4 py-3 text-sm text-slate-100 placeholder:text-slate-600 focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label htmlFor="password" className="mb-2 block text-xs font-medium text-slate-300">
                  Master Key
                </label>
                <input
                  id="password"
                  type="password"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  value={password}
                  placeholder="Your key"
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  minLength={mode === "register" ? 6 : undefined}
                  className="w-full rounded-lg border border-slate-800 bg-[#0B0F17] px-4 py-3 text-sm text-slate-100 placeholder:text-slate-600 focus:border-emerald-500 focus:outline-none"
                />
                {mode === "register" && (
                  <div className="mt-3">
                    <div className="flex gap-1.5" aria-label={`Password strength ${passwordStrength} out of 4`}>
                      {[0, 1, 2, 3].map((level) => (
                        <span
                          key={level}
                          className={`h-1 flex-1 rounded-full transition-colors duration-200 ${
                            passwordStrength <= level
                              ? "bg-slate-800"
                              : passwordStrength <= 2
                                ? "bg-red-500"
                                : passwordStrength === 3
                                  ? "bg-orange-500"
                                  : "bg-emerald-400"
                          }`}
                        />
                      ))}
                    </div>
                    <p
                      aria-live="polite"
                      className={`mt-2 text-[11px] transition-colors duration-200 ${
                        passwordStrength === 0
                          ? "text-slate-500"
                          : passwordStrength <= 2
                            ? "text-red-500"
                            : passwordStrength === 3
                              ? "text-orange-500"
                              : "text-emerald-400"
                      }`}
                    >
                      Password strength: {["Enter a password", "Weak", "Weak", "Medium", "Strong"][passwordStrength]}
                    </p>
                  </div>
                )}
              </div>

              {/* Terms Checkbox */}
              {mode === "register" && (
                <label className="flex cursor-pointer items-start gap-2 text-xs leading-5 text-slate-400">
                  <input
                    type="checkbox"
                    checked={acceptedTerms}
                    onChange={(event) => setAcceptedTerms(event.target.checked)}
                    required
                    className="mt-0.5 h-4 w-4 shrink-0 accent-emerald-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0B0F17]"
                  />
                  <span>
                    I agree to the{" "}
                    <a href="https://vortech.markets/terms.html" target="_blank" rel="noopener noreferrer" className="text-emerald-300 underline-offset-2 hover:underline">
                      Terms of Service
                    </a>{" "}
                    and{" "}
                    <a href="https://vortech.markets/privacy-policy.html" target="_blank" rel="noopener noreferrer" className="text-emerald-300 underline-offset-2 hover:underline">
                      Privacy Policy
                    </a>
                  </span>
                </label>
              )}

              {/* Login Options */}
              {mode === "login" && (
                <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
                  <label className="inline-flex items-center gap-2 text-slate-400">
                    <input
                      type="checkbox"
                      checked={rememberInstance}
                      onChange={(event) => setRememberInstance(event.target.checked)}
                      className="h-4 w-4 accent-emerald-500"
                    />
                    Remember Instance
                  </label>
                  <a href="mailto:contact@vortech.markets?subject=GenX%20Master%20Key%20Assistance" className="text-emerald-300 hover:text-emerald-200">
                    Forgot Key?
                  </a>
                </div>
              )}

              {/* Error & Success Messages */}
              {error && (
                <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/5 px-3 py-2 text-sm text-red-300">
                  {error}
                </div>
              )}
              {successMsg && (
                <div role="alert" className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 px-3 py-2 text-sm text-emerald-300">
                  {successMsg}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || (mode === "register" && !acceptedTerms)}
                className="btn-primary w-full justify-center disabled:cursor-not-allowed disabled:opacity-60"
              >
                <span className="relative z-[1] inline-flex items-center gap-2">
                  {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
                  {!loading && <ArrowUpRight className="h-4 w-4" />}
                </span>
              </button>
            </form>

            <div className="my-6 flex items-center gap-4 text-xs text-slate-500">
              <span className="h-px flex-1 bg-slate-800" />
              <span>or</span>
              <span className="h-px flex-1 bg-slate-800" />
            </div>

            {/* Google OAuth Button */}
            <button
              type="button"
              onClick={handleGoogleLogin}
              className="flex w-full items-center justify-center gap-3 rounded-lg border border-slate-800 bg-[#0B0F17] px-4 py-3 text-sm font-medium text-slate-200 transition-colors hover:border-slate-600 hover:bg-slate-800/50"
            >
              <svg aria-hidden="true" viewBox="0 0 48 48" className="h-5 w-5">
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.72 7.18l7.62 5.91c4.45-4.11 7.14-10.16 7.14-17.56Z" />
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.9-5.8l-7.62-5.91c-2.12 1.42-4.84 2.26-8.28 2.26-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48Z" />
                <path fill="#FBBC05" d="M10.53 28.59a14.4 14.4 0 0 1 0-9.18l-7.98-6.19a23.9 23.9 0 0 0 0 21.56l7.98-6.19Z" />
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5Z" />
              </svg>
              {mode === "login" ? "Continue with Google" : "Sign up with Google"}
            </button>

            {/* Mode Toggle */}
            <div className="mt-7 border-t border-slate-800/80 pt-6 text-center text-sm text-slate-400">
              {mode === "login" ? (
                <>
                  Don&apos;t have an account?{" "}
                  <button onClick={() => setMode("register")} className="font-medium text-emerald-300 hover:text-emerald-200">
                    Register
                  </button>
                </>
              ) : (
                <>
                  Already registered?{" "}
                  <button onClick={() => setMode("login")} className="font-medium text-emerald-300 hover:text-emerald-200">
                    Sign in
                  </button>
                </>
              )}
            </div>
            
            <div className="mt-6 flex items-center justify-center gap-2 text-[10px] font-mono uppercase tracking-widest text-slate-600">
              <LockKeyhole className="h-3 w-3" /> Secure Access
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}