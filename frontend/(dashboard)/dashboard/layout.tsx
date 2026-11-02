"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeftRight,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  CircleDollarSign,
  FileText,
  LayoutDashboard,
  LogOut,
  Database,
  Radio,
  Users,
  X,
} from "lucide-react";
import { clearToken, getToken, isAdmin } from "@/lib/auth";
import { useLiveSocket } from "@/lib/useLiveSocket";
import { TOKEN_CONFIG } from "@/lib/tokenConfig";
import DashboardFooter from "@/components/DashboardFooter";

const links = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard, adminOnly: false },
  { href: "/dashboard/performance", label: "Performance", icon: BarChart3, adminOnly: false },
  { href: "/dashboard/vtgx", label: TOKEN_CONFIG.symbol, icon: CircleDollarSign, adminOnly: false },
  { href: "/dashboard/trades", label: "Trades", icon: ArrowLeftRight, adminOnly: false },
  { href: "/dashboard/live", label: "Live Sessions", icon: Radio, adminOnly: false },
  { href: "/dashboard/mining", label: "Mining", icon: Database, adminOnly: false },
  { href: "/dashboard/audit", label: "Audit", icon: FileText, adminOnly: false },
  { href: "/dashboard/users", label: "Users", icon: Users, adminOnly: true },
];

const SIDEBAR_STORAGE_KEY = "genx_dashboard_sidebar_collapsed";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [isClient, setIsClient] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { connected, updateCount } = useLiveSocket();
  const role = isAdmin() ? "Admin" : "User";

  useEffect(() => {
    setIsClient(true);
    setCollapsed(localStorage.getItem(SIDEBAR_STORAGE_KEY) === "true");
  }, []);

  useEffect(() => {
    if (!isClient) return;

    const timer = setTimeout(() => {
      if (!getToken()) window.location.replace("/login");
    }, 150);

    return () => clearTimeout(timer);
  }, [isClient, pathname]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
        return;
      }

      const target = event.target;
      const isTyping =
        target instanceof HTMLElement &&
        target.matches("input, textarea, select, [contenteditable='true']");
      if (
        event.key === "[" &&
        !isTyping &&
        !event.metaKey &&
        !event.ctrlKey &&
        !event.altKey
      ) {
        setCollapsed((current) => {
          const next = !current;
          localStorage.setItem(SIDEBAR_STORAGE_KEY, String(next));
          return next;
        });
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  function toggleSidebar() {
    setCollapsed((current) => {
      const next = !current;
      localStorage.setItem(SIDEBAR_STORAGE_KEY, String(next));
      return next;
    });
  }

  if (!isClient) {
    return (
      <div className="flex min-h-[calc(100svh-4.25rem)] items-center justify-center text-sm text-slate-500">
        Loading dashboard…
      </div>
    );
  }

  const visibleLinks = links.filter((link) => !link.adminOnly || isAdmin());

  return (
    <div className="flex min-h-[calc(100svh-var(--navbar-height))] flex-col bg-[#0B0F17] text-slate-100">
      <div className="flex-1 lg:flex">
      <div className="flex h-14 items-center justify-end border-b border-slate-800/80 px-4 lg:hidden">
        <button
          type="button"
          aria-label={mobileOpen ? "Close dashboard navigation" : "Open dashboard navigation"}
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((open) => !open)}
          className="rounded-md border border-slate-700 p-2 text-slate-300 hover:text-white"
        >
          {mobileOpen ? <X size={18} /> : <ChevronRight size={18} />}
        </button>
      </div>

      <button
        type="button"
        aria-label="Close dashboard navigation"
        aria-hidden={!mobileOpen}
        tabIndex={mobileOpen ? 0 : -1}
        onClick={() => setMobileOpen(false)}
        className={`fixed inset-x-0 bottom-0 top-[var(--navbar-height)] z-40 cursor-default bg-black/60 transition-opacity duration-300 ease-out motion-reduce:transition-none lg:hidden ${
          mobileOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />

      <aside
        className={`fixed left-0 top-[var(--navbar-height)] z-[60] flex h-[calc(100svh-var(--navbar-height))] w-64 -translate-x-full flex-col overflow-hidden border-r border-slate-800/80 bg-[#0D131D] px-3 py-4 shadow-[16px_0_40px_rgba(0,0,0,0.18)] transition-[width,transform] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none lg:translate-x-0 ${
          collapsed ? "lg:w-16" : "lg:w-64"
        } ${mobileOpen ? "translate-x-0" : ""}`}
      >
        <nav aria-label="Dashboard sections" className="flex flex-col gap-1">
          {visibleLinks.map(({ href, label, icon: Icon }) => {
            const active =
              pathname === href || (href !== "/dashboard" && pathname.startsWith(`${href}/`));
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                title={collapsed ? label : undefined}
                className={`flex min-h-10 items-center gap-3 rounded-md border px-3 text-sm transition-colors duration-200 ${
                  collapsed ? "lg:justify-center lg:px-0" : ""
                } ${
                  active
                    ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                    : "border-transparent text-slate-400 hover:border-slate-800 hover:bg-slate-800/40 hover:text-slate-100"
                }`}
              >
                <Icon size={17} strokeWidth={1.8} aria-hidden="true" />
                <span
                  className={`overflow-hidden whitespace-nowrap transition-[max-width,opacity,transform] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none ${
                    collapsed
                      ? "lg:max-w-0 lg:-translate-x-1 lg:opacity-0"
                      : "lg:max-w-40 lg:translate-x-0 lg:opacity-100"
                  }`}
                >
                  {label}
                </span>
              </Link>
            );
          })}
        </nav>

        <button
          type="button"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
          aria-keyshortcuts="["
          title={collapsed ? "Expand sidebar ([)" : "Collapse sidebar ([)"}
          onClick={toggleSidebar}
          className="mt-3 hidden min-h-10 w-full items-center justify-center rounded-md border border-slate-800 px-3 text-sm text-slate-400 transition-colors hover:border-slate-700 hover:bg-slate-800/40 hover:text-slate-100 lg:flex"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>

        <div className="flex-1" aria-hidden="true" />

        <div className={`mb-3 flex items-center gap-2 rounded-md border border-slate-800/80 px-3 py-2 text-xs ${
          collapsed ? "lg:justify-center lg:px-0" : ""
        }`}>
          <span
            className={`h-2 w-2 shrink-0 rounded-full ${
              connected ? "bg-emerald-400" : "bg-amber-400"
            }`}
            aria-hidden="true"
          />
          <span
            className={`overflow-hidden whitespace-nowrap text-slate-400 transition-[max-width,opacity,transform] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none ${
              collapsed
                ? "lg:max-w-0 lg:-translate-x-1 lg:opacity-0"
                : "lg:max-w-40 lg:translate-x-0 lg:opacity-100"
            }`}
          >
            {connected ? "Live connection" : "Reconnecting"}
          </span>
          {updateCount > 0 && (
            <span
              className={`ml-auto overflow-hidden whitespace-nowrap font-mono text-[10px] text-slate-500 transition-[max-width,opacity] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none ${
                collapsed ? "lg:max-w-0 lg:opacity-0" : "lg:max-w-12 lg:opacity-100"
              }`}
            >
              {updateCount}
            </span>
          )}
        </div>
        <div
          className={`mb-3 overflow-hidden whitespace-nowrap px-3 text-xs text-slate-500 transition-[max-height,opacity,transform] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none ${
            collapsed
              ? "lg:max-h-0 lg:-translate-y-1 lg:opacity-0"
              : "lg:max-h-8 lg:translate-y-0 lg:opacity-100"
          }`}
        >
          Signed in as <span className="text-slate-300">{role}</span>
        </div>
        <button
          type="button"
          onClick={() => {
            clearToken();
            window.location.replace("/login");
          }}
          aria-label="Sign out"
          title={collapsed ? "Sign out" : undefined}
          className={`flex min-h-10 items-center gap-3 rounded-md border border-slate-800 px-3 text-left text-sm text-slate-400 hover:border-slate-700 hover:text-slate-100 ${
            collapsed ? "lg:justify-center lg:px-0" : ""
          }`}
        >
          <LogOut size={16} aria-hidden="true" />
          <span className={collapsed ? "lg:hidden" : ""}>Sign out</span>
        </button>
        <span className="sr-only">Sidebar toggle keyboard shortcut: [</span>
      </aside>

      <div
        aria-hidden="true"
        className={`hidden shrink-0 transition-[width] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none lg:block ${
          collapsed ? "lg:w-16" : "lg:w-64"
        }`}
      />

      <main className="min-w-0 flex-1 p-4 transition-[padding] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none md:p-6 xl:p-8">{children}</main>
      </div>
      <DashboardFooter />
    </div>
  );
}
