"use client";

import { motion } from "framer-motion";

import { useSidebarStore } from "@/store/sidebar-store";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { SidebarContent } from "@/components/layout/sidebar-content";

/** Fixed desktop sidebar. Hidden below `lg`, replaced by the drawer. */
export function Sidebar() {
  const { isCollapsed, toggleCollapsed } = useSidebarStore();

  return (
    <motion.aside
      initial={false}
      animate={{ width: isCollapsed ? 76 : 264 }}
      transition={{ type: "spring", stiffness: 320, damping: 32 }}
      className="fixed inset-y-0 left-0 z-40 hidden border-r border-sidebar-border bg-sidebar lg:block"
    >
      <SidebarContent
        collapsed={isCollapsed}
        onToggleCollapsed={toggleCollapsed}
        showCollapseControl
      />
    </motion.aside>
  );
}

/** Off-canvas sidebar for mobile / tablet, backed by shadcn's Sheet (Radix Dialog). */
export function MobileSidebar() {
  const { isMobileOpen, setMobileOpen } = useSidebarStore();

  return (
    <Sheet open={isMobileOpen} onOpenChange={setMobileOpen}>
      <SheetContent side="left" className="p-0">
        <SheetTitle className="sr-only">Navigation</SheetTitle>
        <SidebarContent onNavigate={() => setMobileOpen(false)} />
      </SheetContent>
    </Sheet>
  );
}
