"use client";

import type { MonthlyReturn } from "@/lib/dashboardAnalytics";

export default function MonthlyHeatmap({
  returns,
}: {
  returns: MonthlyReturn[];
}) {
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const years = Array.from(new Set(returns.map((item) => item.year))).slice(-5);

  return (
    <section className="min-w-0 rounded-lg border border-slate-800 bg-[#111723] p-4">
      <div className="mb-4">
        <h2 className="text-sm font-medium text-slate-100">Monthly returns</h2>
        <p className="mt-1 text-[11px] text-slate-500">Calculated from available equity snapshots</p>
      </div>
      {years.length === 0 ? (
        <div className="flex min-h-20 items-center text-xs text-slate-500">
          Monthly performance will appear when equity history is available.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <div className="min-w-[680px]">
            <div className="grid grid-cols-[44px_repeat(12,minmax(0,1fr))] gap-1">
              <span />
              {months.map((month) => (
                <span key={month} className="pb-1 text-center text-[9px] text-slate-500">{month}</span>
              ))}
              {years.map((year) => (
                <div key={year} className="contents">
                  <span className="self-center font-mono text-[10px] text-slate-500">{year}</span>
                  {months.map((month, index) => {
                    const item = returns.find((entry) => entry.year === year && entry.month === index);
                    return (
                      <span
                        key={`${year}-${month}`}
                        title={item ? `${month} ${year}: ${item.value >= 0 ? "+" : ""}${item.value.toFixed(2)}%` : `${month} ${year}: no data`}
                        aria-label={item ? `${month} ${year}: ${item.value.toFixed(2)} percent` : `${month} ${year}: no data`}
                        className={`flex h-8 items-center justify-center rounded-sm font-mono text-[9px] ${
                          !item
                            ? "border border-slate-800/60 bg-[#0B0F17]"
                            : item.value >= 0
                            ? "border border-emerald-500/15 bg-emerald-500/15 text-emerald-200"
                            : "border border-rose-500/15 bg-rose-500/15 text-rose-300"
                        }`}
                      >
                        {item ? `${item.value >= 0 ? "+" : ""}${item.value.toFixed(1)}%` : "—"}
                      </span>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
