"use client";
import useSWR from "swr";
import { api } from "./api";
import { Plan } from "./usePlans";

export interface AdminUser {
  id: number;
  email: string;
  full_name?: string | null;
  role: "admin" | "user" | "viewer" | string;
  is_active: boolean;
  plan?: Plan | null;
  last_login?: string | null;
  created_at?: string | null;
}

export function useUsers() {
  const { data, error, isLoading, mutate } = useSWR<AdminUser[]>(
    "/api/auth/users",
    (url) => api.get(url).then((r) => r.data),
    { revalidateOnFocus: true, refreshInterval: 30000 }
  );
  return { users: data ?? [], error, isLoading, mutate };
}

export async function updateUser(id: number, patch: Partial<{
  role: string; 
  is_active: boolean; 
  plan_code: string; 
  full_name: string;
  force_verify: boolean;  // <-- Add this line
}>) {
  const r = await api.patch(`/api/auth/users/${id}`, patch);
  return r.data as AdminUser;
}

export async function deleteUser(id: number) {
  await api.delete(`/api/auth/users/${id}`);
}

export function useUserActivity(id: number | null) {
  const { data } = useSWR(
    id ? `/api/auth/users/${id}/activity` : null,
    (url) => api.get(url).then((r) => r.data),
    { revalidateOnFocus: false }
  );
  return data ?? [];
}