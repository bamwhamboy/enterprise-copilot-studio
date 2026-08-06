import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";

import type { AuthUser, TokenResponse } from "@/types/auth";

const STORAGE_KEY = "ecs-auth-state";
const ENGINE_KEY = "ecs-auth-storage-engine"; // "local" | "session"

function resolveEngine(): Storage | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ENGINE_KEY) === "session"
    ? window.sessionStorage
    : window.localStorage;
}

/**
 * Reads/writes to localStorage or sessionStorage depending on the
 * user's Remember Me choice at login. sessionStorage is cleared
 * automatically and reliably by the browser itself when the tab/
 * browser closes -- a guarantee a manual "clear on pagehide" handler
 * can't make, since that event doesn't fire in every close scenario
 * (this replaced an earlier, less reliable pagehide-based approach).
 */
const dynamicStorage: StateStorage = {
  getItem: (name) => resolveEngine()?.getItem(name) ?? null,
  setItem: (name, value) => resolveEngine()?.setItem(name, value),
  removeItem: (name) => resolveEngine()?.removeItem(name),
};

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
      setTokens: (tokens, rememberMe) => {
        if (typeof window !== "undefined" && rememberMe !== undefined) {
          const previousEngine = window.localStorage.getItem(ENGINE_KEY);
          const nextEngine = rememberMe ? "local" : "session";
          if (previousEngine !== nextEngine) {
            // Switching engines -- clear whichever one we're leaving so a
            // stale copy can never be read back on a later visit.
            const previousStorage =
              previousEngine === "session" ? window.sessionStorage : window.localStorage;
            previousStorage.removeItem(STORAGE_KEY);
          }
          window.localStorage.setItem(ENGINE_KEY, nextEngine);
        }
        set((state) => ({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          rememberMe: rememberMe ?? state.rememberMe,
        }));
      },
      setUser: (user) => set({ user }),
      logout: () => {
        if (typeof window !== "undefined") {
          window.sessionStorage.removeItem(STORAGE_KEY);
          window.localStorage.removeItem(STORAGE_KEY);
          window.localStorage.removeItem(ENGINE_KEY);
        }
        set({ accessToken: null, refreshToken: null, user: null });
      },
      setHasHydrated: (value) => set({ hasHydrated: value }),
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => dynamicStorage),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);

/** Non-hook accessor for use outside React (e.g. the fetch wrapper). */
export function getAuthState() {
  return useAuthStore.getState();
}
