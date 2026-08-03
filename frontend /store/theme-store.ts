import { create } from "zustand";

export type ThemeMode = "light" | "dark";

interface ThemeState {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  toggleMode: () => void;
}

const STORAGE_KEY = "ecs-theme-mode";

function applyModeToDocument(mode: ThemeMode) {
  if (typeof document === "undefined") return;
  document.documentElement.classList.toggle("dark", mode === "dark");
}

function getInitialMode(): ThemeMode {
  if (typeof window === "undefined") return "light";
  const stored = window.localStorage.getItem(STORAGE_KEY) as ThemeMode | null;
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export const useThemeStore = create<ThemeState>()((set, get) => ({
  mode: "light",
  setMode: (mode) => {
    set({ mode });
    applyModeToDocument(mode);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, mode);
    }
  },
  toggleMode: () => {
    const next = get().mode === "dark" ? "light" : "dark";
    get().setMode(next);
  },
}));

/** Call once on client mount to sync store + DOM with persisted/system preference. */
export function initializeTheme() {
  const initial = getInitialMode();
  useThemeStore.setState({ mode: initial });
  applyModeToDocument(initial);
}
