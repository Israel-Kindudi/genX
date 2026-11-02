"use client";
import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { AdminUser } from "@/lib/useUsers";
import PlanBadge from "./PlanBadge";

interface Props {
  users: AdminUser[];
  loading?: boolean;
  onSelect: (u: AdminUser) => void;
  selectedId?: number | null;
}

export default function UsersTable({ users, loading, onSelect, selectedId }: Props) {
  const [q, setQ] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [planFilter, setPlanFilter] = useState("all");

  const filtered = useMemo(() => {
    return users.filter((u) => {
      if (q && !`${u.email} ${u.full_name ?? ""}`.toLowerCase().includes(q.toLowerCase())) return false;
      if (roleFilter !== "all" && u.role !== roleFilter) return false;
      if (statusFilter === "active" && !u.is_active) return false;
      if (statusFilter === "suspended" && u.is_active) return false;
      
      // Fix: use the correct plan codes
      if (planFilter !== "all" && (u.plan?.code ?? "trial") !== planFilter) return false;
      return true;
    });
  }, [users, q, roleFilter, statusFilter, planFilter]);

  return (
    <div className="rounded-xl border border-slate-800 bg-[#111723]">
      {/* filters */}
      <div className="flex flex-wrap gap-2 border-b border-slate-800 p-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Search email or name…"
            className="w-full rounded-lg border border-slate-700 bg-[#0B0F17] py-2 pl-9 pr-3 text-sm text-slate-200 placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none"
          />
        </div>
        <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}
          className="rounded-lg border border-slate-700 bg-[#0B0F17] px-3 py-2 text-sm text-slate-200">
          <option value="all">All roles</option>
          <option value="admin">Admin</option>
          <option value="user">User</option>
          <option value="viewer">Viewer</option>
        </select>
        <select value={planFilter} onChange={(e) => setPlanFilter(e.target.value)}
          className="rounded-lg border border-slate-700 bg-[#0B0F17] px-3 py-2 text-sm text-slate-200">
          <option value="all">All plans</option>
          <option value="trial">Trial</option>
          <option value="starter">Starter</option>
          <option value="pro">Pro</option>
          <option value="firm">Firm</option>
          <option value="firm_xl">Firm XL</option>
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-slate-700 bg-[#0B0F17] px-3 py-2 text-sm text-slate-200">
          <option value="all">All status</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
        </select>
      </div>

      {/* table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-[#0B0F17] text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3 text-left">Email</th>
              <th className="px-4 py-3 text-left">Role</th>
              <th className="px-4 py-3 text-left">Plan</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Last login</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-500">Loading…</td></tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-500">No users found</td></tr>
            )}
            {filtered.map((u) => (
              <tr key={u.id}
                onClick={() => onSelect(u)}
                className={`cursor-pointer border-t border-slate-800/70 transition hover:bg-slate-800/40 ${selectedId === u.id ? "bg-slate-800/60" : ""}`}>
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-100">{u.email}</div>
                  {u.full_name && <div className="text-xs text-slate-500">{u.full_name}</div>}
                </td>
                <td className="px-4 py-3">
                  <span className="rounded-md border border-slate-700 px-2 py-0.5 text-xs text-slate-300">
                    {u.role}
                  </span>
                </td>
                <td className="px-4 py-3"><PlanBadge plan={u.plan} /></td>
                <td className="px-4 py-3">
                  {u.is_active
                    ? <span className="text-emerald-400">● active</span>
                    : <span className="text-red-400">● suspended</span>}
                </td>
                <td className="px-4 py-3 text-slate-400">
                  {u.last_login ? new Date(u.last_login).toLocaleString("en-US") : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}