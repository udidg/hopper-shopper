/* ── Auth Store (Zustand) ────────────────────────────────────── */

import { create } from "zustand";
import type { User } from "@/types";
import { authenticateTelegram } from "@/services/api";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (initData: string) => Promise<void>;
  logout: () => void;
  setToken: (token: string) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem("access_token"),
  isAuthenticated: !!localStorage.getItem("access_token"),
  isLoading: false,
  error: null,

  login: async (initData: string) => {
    set({ isLoading: true, error: null });
    try {
      const result = await authenticateTelegram(initData);
      localStorage.setItem("access_token", result.access_token);
      set({
        user: result.user,
        token: result.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Authentication failed",
        isLoading: false,
      });
    }
  },

  logout: () => {
    localStorage.removeItem("access_token");
    set({ user: null, token: null, isAuthenticated: false });
  },

  setToken: (token: string) => {
    localStorage.setItem("access_token", token);
    set({ token, isAuthenticated: true });
  },
}));
