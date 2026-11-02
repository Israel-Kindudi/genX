"use client";

import { useMemo, useState } from "react";
import { useLiveTrades, type LiveTrade } from "@/lib/useLiveTrades";

type Filter = "ALL" | "OPEN" | "CLOSED" | "BUY" | "SELL";

export default function TradesPage() {
  const { trades, connected } = useLiveTrades(500, 300);
  const [filter, setFilter] = useState<Filter>("ALL");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<LiveTrade | null>(null);
  const filtered = useMemo(
    () =>
      trades.filter((trade) => {
        if (query && !trade.symbol.toLowerCase().includes(query.trim().toLowerCase())) return false;
        if (filter === "OPEN") return trade.status === "open";
        if (filter === "CLOSED") return trade.status === "closed";
        if (filter === "BUY" || filter === "SELL") return trade.action === filter;
        return true;
      }),
    [trades, filter, query]
  );

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-[10px] font-mono uppercase tracking-[0.18em] text-emerald-300">Execution</p>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-100">Trades</h1>
          <p className="mt-1 text-sm text-slate-400">Live and completed executions reported by the GenX engine.</p>
        </div>
        <span className={`rounded border px-2.5 py-1.5 font-mono text-[10px] ${
          connected ? "border-emerald-500/25 text-emerald-300" : "border-amber-500/25 text-amber-300"
        }`}>{connected ? "LIVE" : "RECONNECTING"}</span>
      </header>

      <section className="overflow-hidden rounded-lg border border-slate-800 bg-[#111723]">
        <div className="flex flex-col gap-3 border-b border-slate-800 p-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-1" role="group" aria-label="Filter trades">
            {(["ALL", "OPEN", "CLOSED", "BUY", "SELL"] as const).map((item) => (
              <button
                key={item}
                type="button"
                aria-pressed={filter === item}
                onClick={() => setFilter(item)}
                className={`rounded border px-2.5 py-1.5 text-[10px] ${
                  filter === item
                    ? "border-emerald-500/25 bg-emerald-500/5 text-emerald-300"
                    : "border-transparent text-slate-400 hover:border-slate-700 hover:text-slate-200"
                }`}
              >
                {item}
              </button>
            ))}
          </div>
          <label className="sr-only" htmlFor="trade-symbol-filter">Filter by symbol</label>
          <input
            id="trade-symbol-filter"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filter symbol…"
            className="w-full rounded border border-slate-800 bg-[#0B0F17] px-3 py-2 text-xs text-slate-200 placeholder:text-slate-500 focus:border-emerald-500/40 focus:outline-none sm:max-w-xs"
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-xs">
            <thead className="border-b border-slate-800 bg-[#0D131D] text-[9px] tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Side / Symbol</th>
                <th className="px-4 py-3 font-medium">Strategy</th>
                <th className="px-4 py-3 text-right font-medium">Entry</th>
                <th className="px-4 py-3 text-right font-medium">Exit</th>
                <th className="px-4 py-3 text-right font-medium">Volume</th>
                <th className="px-4 py-3 text-right font-medium">PnL</th>
                <th className="px-4 py-3 text-right font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((trade) => (
                <tr
                  key={trade.ticket}
                  className="border-b border-slate-800/70 text-slate-300 transition-colors hover:bg-slate-800/20"
                >
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => setSelected(trade)}
                      className="text-left"
                      aria-label={`View ${trade.symbol} ${trade.action} trade details`}
                    >
                      <span className={`mr-2 rounded border px-1.5 py-0.5 font-mono text-[9px] ${
                        trade.action === "BUY"
                          ? "border-emerald-500/20 text-emerald-300"
                          : "border-slate-700 text-slate-300"
                      }`}>{trade.action}</span>
                      <span className="font-mono text-slate-100">{trade.symbol}</span>
                    </button>
                  </td>
                  <td className="max-w-[220px] truncate px-4 py-3 text-slate-400">{trade.strategy || "—"}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{trade.entry_price?.toFixed(5) ?? "—"}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{trade.exit_price?.toFixed(5) ?? "—"}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{trade.lot.toFixed(2)}</td>
                  <td className={`px-4 py-3 text-right font-mono tabular-nums ${
                    trade.pnl == null ? "text-slate-500" : trade.pnl < 0 ? "text-rose-400" : "text-emerald-300"
                  }`}>{trade.pnl == null ? "—" : `${trade.pnl >= 0 ? "+" : "−"}$${Math.abs(trade.pnl).toFixed(2)}`}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={`rounded px-1.5 py-1 text-[9px] ${
                      trade.status === "open" ? "bg-amber-500/10 text-amber-300" : "bg-slate-800 text-slate-400"
                    }`}>{trade.status.toUpperCase()}</span>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-14 text-center text-xs text-slate-500">
                    {trades.length === 0 ? "Waiting for trades from the live engine." : "No trades match these filters."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {selected && <TradeDetails trade={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function TradeDetails({ trade, onClose }: { trade: LiveTrade; onClose: () => void }) {
  const rows = [
    ["Ticket", String(trade.ticket)],
    ["Session", trade.session_id],
    ["Strategy", trade.strategy || "—"],
    ["Entry time", trade.entry_time ? new Date(trade.entry_time).toLocaleString("en-US") : "—"],
    ["Exit time", trade.exit_time ? new Date(trade.exit_time).toLocaleString("en-US") : "—"],
    ["Stop loss", trade.sl?.toFixed(5) ?? "—"],
    ["Take profit", trade.tp?.toFixed(5) ?? "—"],
  ];

  return (
    <div className="fixed inset-0 z-[60] flex justify-end bg-black/60" role="presentation" onMouseDown={onClose}>
      <section
        aria-label={`${trade.symbol} trade details`}
        role="dialog"
        aria-modal="true"
        className="h-full w-full max-w-md overflow-y-auto border-l border-slate-800 bg-[#111723] p-5 shadow-xl"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between border-b border-slate-800 pb-4">
          <div>
            <p className="font-mono text-lg text-slate-100">{trade.symbol}</p>
            <p className="mt-1 text-xs text-slate-500">{trade.action} · {trade.status.toUpperCase()}</p>
          </div>
          <button type="button" aria-label="Close trade details" onClick={onClose} className="rounded border border-slate-800 px-2 py-1 text-slate-400 hover:text-white">×</button>
        </div>
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4 border-b border-slate-800/70 py-3 text-xs">
            <span className="text-slate-500">{label}</span>
            <span className="max-w-[65%] truncate text-right font-mono text-slate-200">{value}</span>
          </div>
        ))}
      </section>
    </div>
  );
}
