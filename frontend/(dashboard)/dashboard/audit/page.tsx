"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function AuditPage() {
  const [reports, setReports] = useState<any[]>([]);

  useEffect(() => {
    api.get("/api/audit/reports").then((r) => setReports(r.data));
  }, []);

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Audit Reports</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {reports.map((r) => (
          <div key={r.file} className="rounded-lg border border-[#1E293B] bg-[#161F2E] p-4">
            <div className="font-mono text-sm truncate mb-2">{r.file}</div>
          </div>
        ))}
        {reports.length === 0 && (
          <div className="py-12 text-center text-slate-500 sm:col-span-2 xl:col-span-3">
            No audit reports yet. Run <code className="font-mono bg-[#0B0F17] px-2 py-1 rounded">audit_suite.py</code>
          </div>
        )}
      </div>
    </div>
  );
}
