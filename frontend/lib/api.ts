import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";



const apiBase = 
  process.env.NEXT_PUBLIC_API_BASE_URL || 
  (typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:8000");

export const api = axios.create({
  baseURL: apiBase,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("genx_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token =
      localStorage.getItem("genx_token") ??
      sessionStorage.getItem("genx_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      console.warn("[api] 401 from", error.config?.url);
    }
    return Promise.reject(error);
  }
);