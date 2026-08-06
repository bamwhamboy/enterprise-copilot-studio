import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { AuthUser, TokenResponse } from "@/types/auth";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  rememberMe: boolean;
  hasHydrated: boolean;
  setTokens: (tokens: TokenResponse, rememberMe?: boolean) => void;
  setUser: (user: AuthUser) => void;
  logout: () => void;
  setHasHydrated: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      rememberMe: true,
      hasHydrated: false,
      setTokens: (tokens, rememberMe) =>
        set((state) => ({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          rememberMe: rememberMe ?? state.rememberMe,
        })),
      setUser: (user) => set({ user }),
      logout: () => set({ accessToken: null, refreshToken: null, user: null }),
      setHasHydrated: (value) => set({ hasHydrated: value }),
    }),
    {
      name: "ecs-auth-state",
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);

/**
 * "Remember Me" semantics: when unchecked, tokens should not survive a
 * browser restart. zustand/persist always writes to localStorage
 * (survives restarts) — so instead of switching storage engines
 * mid-session, this clears the persisted entry on tab close when the
 * user opted out. Called once from Providers (app-wide mount).
 */
export function registerRememberMeCleanup() {
  if (typeof window === "undefined") return () => {};
  const handler = () => {
    if (!useAuthStore.getState().rememberMe) {
      window.localStorage.removeItem("ecs-auth-state");
    }
  };
  window.addEventListener("pagehide", handler);
  return () => window.removeEventListener("pagehide", handler);
}

/** Non-hook accessor for use outside React (e.g. the fetch wrapper). */
export function getAuthState() {
  return useAuthStore.getState();
}
