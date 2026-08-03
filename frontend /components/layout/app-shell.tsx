"use client";

import { motion } from "framer-motion";

import { useIsMobile } from "@/hooks/use-media-query";
import { useMounted } from "@/hooks/use-mounted";
import { useSidebarStore } from "@/store/sidebar-store";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Sidebar, MobileSidebar } from "@/components/layout/sidebar";
import { TopBar } from "@/components/layout/topbar";

interface AppShellProps {
  children: React.ReactNode;
}

/**
 * Reusable shell used by every authenticated route: fixed sidebar,
 * sticky top bar, and a scrollable main content area. The left margin
 * of the content area animates in sync with the sidebar's collapse state,
 * and collapses to 0 on mobile where the sidebar becomes an off-canvas drawer.
 */
export function AppShell({ children }: AppShellProps) {
  const isCollapsed = useSidebarStore((s) => s.isCollapsed);
  const isMobile = useIsMobile();
  const mounted = useMounted();

  // Avoid a flashed offset before the media query resolves on first paint.
  const marginLeft = mounted && !isMobile ? (isCollapsed ? 76 : 264) : 0;

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-background">
        <Sidebar />
        <MobileSidebar />

        <motion.div
          initial={false}
          animate={{ marginLeft }}
          transition={{ type: "spring", stiffness: 320, damping: 32 }}
          className="flex flex-col"
        >
          <TopBar />
          <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">{children}</main>
        </motion.div>
      </div>
    </TooltipProvider>
  );
}
