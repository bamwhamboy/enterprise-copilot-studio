import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SidebarState {
  /** Desktop: rail collapsed to icon-only width */
  isCollapsed: boolean;
  /** Mobile: off-canvas drawer open state */
  isMobileOpen: boolean;
  toggleCollapsed: () => void;
  setCollapsed: (value: boolean) => void;
  setMobileOpen: (value: boolean) => void;
}

export const useSidebarStore = create<SidebarState>()(
  persist(
    (set) => ({
      isCollapsed: false,
      isMobileOpen: false,
      toggleCollapsed: () =>
        set((state) => ({ isCollapsed: !state.isCollapsed })),
      setCollapsed: (value) => set({ isCollapsed: value }),
      setMobileOpen: (value) => set({ isMobileOpen: value }),
    }),
    {
      name: "ecs-sidebar-state",
      partialize: (state) => ({ isCollapsed: state.isCollapsed }),
    }
  )
);
