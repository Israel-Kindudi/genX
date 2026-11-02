"use client";

interface Props {
  label: string;
  used: number;
  cap: number;
  unit?: string;
}

export default function UsageMeter({ label, used, cap, unit = "" }: Props) {
  const unlimited = cap >= 999;
  const pct = unlimited
    ? Math.min(100, used > 0 ? 30 : 0)
    : Math.min(100, (used / Math.max(cap, 1)) * 100);
  const over = !unlimited && cap > 0 && used > cap;
  const near = !unlimited && cap > 0 && used / cap >= 0.8 && !over;

  const barColor = over ? "bg-red-500" : near ? "bg-amber-500" : "bg-emerald-500";

  return (
    <div className="rounded-lg border border-slate-800 bg-[#0B0F17] p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-slate-500">
          {label}
        </span>
        <span
          className={`text-xs font-medium ${
            over ? "text-red-400" : "text-slate-300"
          }`}
        >
          {used}
          {unlimited ? " / ∞" : ` / ${cap}`}
          {unit ? ` ${unit}` : ""}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full transition-all ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {over && (
        <div className="mt-2 text-xs text-red-400">
          Over quota — upgrade to continue
        </div>
      )}
    </div>
  );
}