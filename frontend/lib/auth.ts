/**
 * Auth helpers for GenX frontend.
 * Token is stored in localStorage and decoded for role info.
 */

export function saveToken(token: string, rememberInstance = true) {
  if (typeof window !== "undefined") {
    if (rememberInstance) {
      localStorage.setItem("genx_token", token);
      sessionStorage.removeItem("genx_token");
    } else {
      sessionStorage.setItem("genx_token", token);
      localStorage.removeItem("genx_token");
    }
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("genx_token") ?? sessionStorage.getItem("genx_token");
}

export function clearToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("genx_token");
    sessionStorage.removeItem("genx_token");
  }
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

export function decodeToken(token: string): any {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(
      base64.length + ((4 - (base64.length % 4)) % 4),
      "="
    );
    const decoded = atob(padded);
    return JSON.parse(decoded);
  } catch (e) {
    return null;
  }
}

export function getRole(): string {
  const token = getToken();
  if (!token) return "guest";
  const payload = decodeToken(token);
  return payload?.role || "user";
}

export function isAdmin(): boolean {
  return getRole() === "admin";
}

export function isViewer(): boolean {
  return getRole() === "viewer";
}