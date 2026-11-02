"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function LivePage() {
  const [sessions, setSessions] = useState<any[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [details, setDetails] = useState<any>(null);

  useEffect(() => {
    api.get("/api/live/sessions").then((r) => setSessions(r.data));
  }, []);

  useEffect(() => {
    if (selected) {
      api.get(`/api/live/sessions/${selected}`).then((r) => setDetails(r.data));
    }
  }, [selected]);

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Live Sessions</h1>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="max-h-[600px] overflow-y-auto rounded-lg border border-[#1E293B] bg-[#161F2E] p-4 lg:col-span-1">
          <h2 className="font-semibold mb-4 text-slate-300">Sessions</h2>
          {sessions.map((s) => (
            <button
              key={s.session_id}
              onClick={() => setSelected(s.session_id)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-2 transition-colors ${
                selected === s.session_id
                  ? "bg-[#10B981]/10 text-[#10B981]"
                  : "hover:bg-[#1E293B]/30 text-slate-400"
              }`}
            >
              <div className="font-mono text-xs truncate">{s.session_id}</div>
              <div className="text-xs">
                {s.trades} trades · ${s.pnl.toFixed(2)}
              </div>
            </button>
          ))}
        </div>

        <div className="min-w-0 lg:col-span-2">
          {details ? (
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <Metric label="Total Trades" value={details.trades.length.toString()} />
                <Metric
                  label="Closed"
                  value={details.trades.filter((t: any) => t.status === "closed").length.toString()}
                />
                <Metric
                  label="PnL"
                  value={`$${details.trades
                    .filter((t: any) => t.pnl)
                    .reduce((s: number, t: any) => s + t.pnl, 0)
                    .toFixed(2)}`}
                />
              </div>

              <div className="bg-[#161F2E] border border-[#1E293B] rounded-xl p-4 max-h-[400px] overflow-y-auto">
                <h2 className="font-semibold mb-4 text-slate-300">Trades</h2>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-slate-400 border-b border-[#1E293B]">
                      <th className="py-2">Strategy</th>
                      <th>Symbol</th>
                      <th>Action</th>
                      <th className="text-right">Entry</th>
                      <th className="text-right">PnL</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {details.trades.slice(0, 50).map((t: any, i: number) => (
                      <tr key={i} className="border-b border-[#1E293B]/50">
                        <td className="py-1.5 truncate max-w-[140px]">{t.strategy}</td>
                        <td>{t.symbol}</td>
                        <td className={t.action === "BUY" ? "text-[#10B981]" : "text-red-400"}>
                          {t.action}
                        </td>
                        <td className="text-right">{t.entry_price?.toFixed(2)}</td>
                        <td className={`text-right ${(t.pnl || 0) >= 0 ? "text-[#10B981]" : "text-red-400"}`}>
                          {t.pnl != null ? `$${t.pnl.toFixed(2)}` : "—"}
                        </td>
                        <td className="text-slate-400">{t.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-500">
              Select a session to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[#161F2E] border border-[#1E293B] rounded-xl p-4">
      <div className="text-xl font-bold gradient-text">{value}</div>
      <div className="text-xs text-slate-400 mt-1">{label}</div>
    </div>
  );
}