"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { isAuthenticated, clearToken, isAdmin } from "@/lib/auth";

export default function Header() {
  const pathname = usePathname();
  const [loggedIn, setLoggedIn] = useState(false);
  const [admin, setAdmin] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [floating, setFloating] = useState(false);

  useEffect(() => {
    setLoggedIn(isAuthenticated());
    setAdmin(isAdmin());
  }, [pathname]);

  useEffect(() => {
    let frame = 0;
    const initialY = window.scrollY;
    setFloating(initialY > 40);

    const updateHeader = () => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        const currentY = window.scrollY;
        setFloating((current) =>
          current ? currentY > 10 : currentY > 40
        );
        frame = 0;
      });
    };

    window.addEventListener("scroll", updateHeader, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", updateHeader);
    };
  }, []);

  const links = [
    { href: "/vision", label: "Vision" },
    { href: "/strategies", label: "Strategies" },
    { href: "/research", label: "Research" },
    { href: "/#pricing", label: "Pricing" },
  ];

  const isActive = (href: string) =>
    pathname === href || (href !== "/" && href !== "/#pricing" && pathname.startsWith(`${href}/`));
  const isDashboard = pathname.startsWith("/dashboard");

  return (
    <>
      <nav
        className={isDashboard
          ? "fixed left-0 top-0 z-[100] h-[var(--navbar-height)] w-full border-b border-slate-800/80 bg-[#0B0F17]/95 px-2 shadow-xl shadow-black/30 backdrop-blur-xl"
          : `site-navbar ${floating ? "site-navbar--floating" : ""}`}
      >
      <div className={`mx-auto flex max-w-7xl items-center justify-between gap-5 px-4 py-3 md:px-6 ${isDashboard ? "h-full" : ""}`}>
        <div className="flex min-w-0 shrink-0 flex-col items-start">
          <Link href="/" className="flex items-center gap-3 font-semibold">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/10 text-xl">
              🧬
            </span>
            <span className="gradient-text text-lg">GenX</span>
          </Link>
          <span className="ml-[3.25rem] -mt-1 font-mono text-[8px] font-semibold uppercase tracking-[0.12em] text-slate-400 sm:text-[9px]">
            Powered by Vortech Markets
          </span>
        </div>

        <div className="hidden items-center gap-1 md:flex">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`rounded-full px-3 py-2 text-sm text-slate-400 transition-colors hover:text-slate-100 ${
                isActive(l.href)
                  ? "bg-emerald-500/10 text-emerald-300 ring-1 ring-inset ring-emerald-500/20"
                  : ""
              }`}
            >
              {l.label}
            </Link>
          ))}

          {loggedIn ? (
            <>
              <Link href="/dashboard" className="btn-primary px-4 py-2 text-sm hover:text-slate-100">
                Dashboard →
              </Link>
              <Link
                href="/dashboard/billing"
                className={`rounded-full px-3 py-2 text-sm transition-colors hover:text-slate-100 ${
                  isActive("/dashboard/billing")
                    ? "text-emerald-300"
                    : "text-slate-400"
                }`}
              >
                Billing
              </Link>
              {admin && (
                <Link
                  href="/dashboard/users"
                  className={`rounded-full px-3 py-2 text-sm transition-colors hover:text-slate-100 ${
                    isActive("/dashboard/users")
                      ? "text-emerald-300"
                      : "text-slate-400"
                  }`}
                >
                  Users
                </Link>
              )}
              <button
                onClick={() => {
                  clearToken();
                  setLoggedIn(false);
                  window.location.href = "/";
                }}
                className="rounded-full px-3 py-2 text-sm text-slate-400 transition-colors hover:text-slate-100"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link href="/login" className="btn-primary px-4 py-2 text-sm hover:text-slate-100">
              Get started →
            </Link>
          )}
        </div>

        <button
          aria-label={mobileOpen ? "Close navigation menu" : "Open navigation menu"}
          aria-expanded={mobileOpen}
          className="rounded-lg border border-slate-800 px-3 py-2 text-lg text-slate-300 transition-colors hover:border-slate-700 hover:text-slate-100 md:hidden"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? "✕" : "☰"}
        </button>
      </div>

      {mobileOpen && (
        <div className="absolute left-0 right-0 top-full space-y-3 rounded-b-2xl border border-slate-800 bg-[#111723]/95 px-6 py-4 shadow-xl backdrop-blur-xl md:hidden">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`block rounded-full px-3 py-2 text-sm text-slate-400 transition-colors hover:text-slate-100 ${
                isActive(l.href)
                  ? "bg-emerald-500/10 text-emerald-300"
                  : ""
              }`}
              onClick={() => setMobileOpen(false)}
            >
              {l.label}
            </Link>
          ))}
          {loggedIn ? (
            <>
              <Link
                href="/dashboard"
                className="block text-emerald-300 transition-colors hover:text-slate-100"
                onClick={() => setMobileOpen(false)}
              >
                Dashboard →
              </Link>
              <Link
                href="/dashboard/billing"
                className="block text-slate-400 transition-colors hover:text-slate-100"
                onClick={() => setMobileOpen(false)}
              >
                Billing
              </Link>
              {admin && (
                <Link
                  href="/dashboard/users"
                  className="block text-slate-400 transition-colors hover:text-slate-100"
                  onClick={() => setMobileOpen(false)}
                >
                  Users
                </Link>
              )}
              <button
                onClick={() => {
                  clearToken();
                  setLoggedIn(false);
                  window.location.href = "/";
                }}
                className="block text-slate-400 transition-colors hover:text-slate-100"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="block text-emerald-300 transition-colors hover:text-slate-100"
              onClick={() => setMobileOpen(false)}
            >
              Get started →
            </Link>
          )}
        </div>
        )}
        </nav>
    </>
  );
}