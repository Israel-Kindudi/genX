import Link from "next/link";

export default function AuthBranding() {
  return (
    <Link href="/" className="inline-flex max-w-full items-center gap-3">
      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-2xl max-lg:h-10 max-lg:w-10 max-lg:text-xl">
        🧬
      </span>
      <span className="min-w-0">
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="gradient-text text-xl font-semibold leading-none">GenX</span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/25 bg-emerald-500/[0.08] px-2 py-1 font-mono text-[8px] uppercase tracking-[0.12em] text-emerald-300 sm:text-[9px]">
            <span className="relative flex h-1.5 w-1.5 shrink-0">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
            </span>
            GENX ENGINE · SECURE ACCESS
          </span>
        </span>
        <span className="mt-1 block font-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-400 sm:text-[10px] sm:tracking-widest">
          Powered by Vortech Markets
        </span>
      </span>
    </Link>
  );
}
