"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function MiningPage() {
  const [runs, setRuns] = useState<any[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [details, setDetails] = useState<any>(null);

  useEffect(() => {
    api.get("/api/mining/runs").then((r) => setRuns(r.data));
  }, []);

  useEffect(() => {
    if (selected) {
      api.get(`/api/mining/runs/${selected}`).then((r) => setDetails(r.data));
    }
  }, [selected]);

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Mining Results</h1>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-lg border border-[#1E293B] bg-[#161F2E] p-4 lg:col-span-1">
          <h2 className="font-semibold mb-4 text-slate-300">Runs</h2>
          {runs.map((r) => (
            <button
              key={r.run_id}
              onClick={() => setSelected(r.run_id)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-2 transition-colors ${
                selected === r.run_id
                  ? "bg-[#10B981]/10 text-[#10B981]"
                  : "hover:bg-[#1E293B]/30 text-slate-400"
              }`}
            >
              <div className="font-mono text-xs truncate">{r.run_id}</div>
              {r.metadata?.accuracy && (
                <div className="text-xs">Acc: {(r.metadata.accuracy * 100).toFixed(1)}%</div>
              )}
            </button>
          ))}
        </div>

        <div className="min-w-0 rounded-lg border border-[#1E293B] bg-[#161F2E] p-4 sm:p-6 lg:col-span-2">
          {details ? (
            <div>
              <h2 className="font-semibold mb-4 text-slate-300">Run details</h2>
              {details.run_metadata && (
                <div className="grid grid-cols-2 gap-4 mb-6">
                  {Object.entries(details.run_metadata).map(([k, v]: any) => (
                    <div key={k}>
                      <div className="text-xs text-slate-500">{k}</div>
                      <div className="text-sm font-mono">{String(v)}</div>
                    </div>
                  ))}
                </div>
              )}
              {details.feature_importance && (
                <div>
                  <h3 className="text-sm text-slate-400 mb-2">Top features</h3>
                  {details.feature_importance.slice(0, 10).map((f: any, i: number) => (
                    <div key={i} className="flex justify-between text-sm py-1 border-b border-[#1E293B]/50">
                      <span>{f.feature}</span>
                      <span className="font-mono text-[#10B981]">
                        {Number(f.importance).toFixed(4)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-500">
              Select a run
            </div>
          )}
        </div>
      </div>
    </div>
  );
}