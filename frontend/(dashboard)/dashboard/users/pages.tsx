"use client";
import { useState } from "react";
import { Users } from "lucide-react";
import { useUsers, AdminUser } from "@/lib/useUsers";
import UsersTable from "@/components/UsersTable";
import UserDrawer from "@/components/UserDrawer";

export default function UsersPage() {
  const { users, isLoading, mutate } = useUsers();
  const [selected, setSelected] = useState<AdminUser | null>(null);

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="h-5 w-5 text-emerald-400" />
          <h1 className="text-xl font-semibold text-slate-100">Users</h1>
          <span className="rounded-full border border-slate-700 px-2 py-0.5 text-xs text-slate-400">
            {users.length}
          </span>
        </div>
      </div>

      <UsersTable
        users={users}
        loading={isLoading}
        onSelect={setSelected}
        selectedId={selected?.id ?? null}
      />

      <UserDrawer
        user={selected}
        onClose={() => setSelected(null)}
        onChanged={() => {
          mutate();
          setSelected(null);
        }}
      />
    </div>
  );
}