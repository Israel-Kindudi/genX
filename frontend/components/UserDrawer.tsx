"use client";
import { useEffect, useState } from "react";
import { X, Trash2, ShieldCheck, Ban, CheckCircle2 } from "lucide-react";
import { AdminUser, updateUser, deleteUser, useUserActivity } from "@/lib/useUsers";
import { usePlans } from "@/lib/usePlans";

interface Props {
  user: AdminUser | null;
  onClose: () => void;
  onChanged: () => void;
}

export default function UserDrawer({ user, onClose, onChanged }: Props) {
  const { plans } = usePlans();
  const activity = useUserActivity(user?.id ?? null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!user) return;
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [user, onClose]);

  if (!user) return null;

  const patch = async (p: Parameters<typeof updateUser>[1]) => {
    setSaving(true);
    try {
      await updateUser(user.id, p);
      onChanged();
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Permanently delete ${user.email}?\n\nThis will erase all their data, trades, and invoices. This cannot be undone.`)) {
      return;
    }
    
    setSaving(true);
    try {
      await deleteUser(user.id);
      onChanged();
      onClose();
    } catch (e) {
      alert("Failed to delete user. Check the console.");
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <aside className="fixed right-0 top-0 z-50 h-full w-full max-w-md overflow-y-auto border-l border-slate-800 bg-[#111723] shadow-2xl">
        <header className="flex items-center justify-between border-b border-slate-800 p-4 sticky top-0 bg-[#111723]/95 backdrop-blur z-10">
          <div>
            <div className="text-sm text-slate-400">User #{user.id}</div>
            <div className="text-lg font-semibold text-slate-100">{user.email}</div>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 hover:bg-slate-800">
            <X className="h-4 w-4 text-slate-400" />
          </button>
        </header>

        <div className="space-y-6 p-4">
          {/* role */}
          <section>
            <label className="mb-2 block text-xs uppercase tracking-wide text-slate-500">Role</label>
            <div className="flex gap-2">
              {["admin", "user", "viewer"].map((r) => (
                <button
                  key={r}
                  disabled={saving}
                  onClick={() => patch({ role: r })}
                  className={`flex-1 rounded-lg border px-3 py-2 text-sm transition ${
                    user.role === r
                      ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
                      : "border-slate-700 text-slate-300 hover:border-slate-600"
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </section>

          {/* plan */}
          <section>
            <label className="mb-2 block text-xs uppercase tracking-wide text-slate-500">Plan</label>
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
              {plans.map((p) => (
                <button
                  key={p.code}
                  disabled={saving}
                  onClick={() => patch({ plan_code: p.code })}
                  className={`rounded-lg border px-3 py-3 text-left transition ${
                    user.plan?.code === p.code
                      ? "border-emerald-500 bg-emerald-500/10"
                      : "border-slate-700 hover:border-slate-600"
                  }`}
                >
                  <div className="text-sm font-medium text-slate-100">{p.name}</div>
                  <div className="text-xs text-slate-400">${p.price_monthly}/mo</div>
                </button>
              ))}
            </div>
          </section>

          {/* account actions */}
          <section>
            <label className="mb-2 block text-xs uppercase tracking-wide text-slate-500">Account Controls</label>
            
            {/* Suspend / Activate */}
            <button
              disabled={saving}
              onClick={() => patch({ is_active: !user.is_active })}
              className={`flex w-full items-center justify-between rounded-lg border px-4 py-3 text-sm transition ${
                user.is_active
                  ? "border-slate-700 hover:border-red-500/50"
                  : "border-red-500/40 bg-red-500/5"
              }`}
            >
              <span className="text-slate-200">
                {user.is_active ? "Account is Active (click to Suspend)" : "Account is Suspended (click to Activate)"}
              </span>
              {user.is_active ? (
                <Ban className="h-4 w-4 text-red-400" />
              ) : (
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
              )}
            </button>

            {/* Force Verify Email */}
            <button
              disabled={saving}
              onClick={() => patch({ force_verify: true })}
              className="flex w-full items-center justify-between rounded-lg border border-slate-700 px-4 py-3 text-sm transition hover:border-emerald-500/50 mt-2"
            >
              <span className="text-slate-200">Force Verify Email</span>
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            </button>
          </section>

          {/* activity */}
          <section>
            <label className="mb-2 block text-xs uppercase tracking-wide text-slate-500">Recent activity</label>
            <div className="max-h-64 space-y-2 overflow-y-auto rounded-lg border border-slate-800 bg-[#0B0F17] p-3">
              {activity.length === 0 && <div className="text-xs text-slate-500">No activity yet</div>}
              {activity.map((a: any) => (
                <div key={a.id} className="text-xs border-b border-slate-800/50 pb-2 last:border-0 last:pb-0">
                  <div className="font-mono text-emerald-300">{a.action}</div>
                  <div className="text-slate-400 break-words">{a.detail}</div>
                  <div className="text-slate-600 mt-1">{new Date(a.created_at).toLocaleString("en-US")}</div>
                </div>
              ))}
            </div>
          </section>

          {/* danger zone */}
          <section className="rounded-lg border border-red-500/30 bg-red-500/5 p-3">
            <div className="mb-2 text-xs uppercase tracking-wide text-red-400">Danger zone</div>
            <button
              disabled={saving}
              onClick={handleDelete}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-red-500/40 px-3 py-2 text-sm text-red-300 hover:bg-red-500/10 transition disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" /> Permanently Delete User
            </button>
            <p className="mt-2 text-[10px] text-red-400/70 text-center">
              This will purge all trades, invoices, and subscriptions associated with this account.
            </p>
          </section>
        </div>
      </aside>
    </>
  );
}