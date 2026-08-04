"use client";

import { Sparkles, ChevronsLeft, ChevronsRight } from "lucide-react";

import { cn } from "@/lib/utils";
import { primaryNavItems, secondaryNavItems } from "@/lib/nav-config";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SidebarNavItem } from "@/components/layout/sidebar-nav-item";

interface SidebarContentProps {
  collapsed?: boolean;
  onNavigate?: () => void;
  onToggleCollapsed?: () => void;
  showCollapseControl?: boolean;
}

export function SidebarContent({
  collapsed,
  onNavigate,
  onToggleCollapsed,
  showCollapseControl,
}: SidebarContentProps) {
  return (
    <div className="flex h-full flex-col">
      <div
        className={cn(
          "flex h-16 items-center gap-2 px-4",
          collapsed && "justify-center px-2"
        )}
      >
        <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-[#5b7cfa] text-primary-foreground shadow-sm">
          <Sparkles className="size-4" />
        </div>
        {!collapsed && (
          <div className="flex flex-col leading-tight">
            <span className="text-sm font-semibold text-sidebar-foreground">
              Copilot Studio
            </span>
            <span className="text-[11px] text-sidebar-foreground/50">
              Enterprise
            </span>
          </div>
        )}
      </div>

      <Separator className="bg-sidebar-border" />

      <ScrollArea className="flex-1 px-3 py-4">
        <nav className="flex flex-col gap-1">
          {primaryNavItems.map((item) => (
            <SidebarNavItem
              key={item.key}
              item={item}
              collapsed={collapsed}
              onNavigate={onNavigate}
            />
          ))}
        </nav>
      </ScrollArea>

      <Separator className="bg-sidebar-border" />

      <div className="flex flex-col gap-1 p-3">
        {secondaryNavItems.map((item) => (
          <SidebarNavItem
            key={item.key}
            item={item}
            collapsed={collapsed}
            onNavigate={onNavigate}
          />
        ))}

        {showCollapseControl && (
          <button
            type="button"
            onClick={onToggleCollapsed}
            className={cn(
              "mt-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-sidebar-foreground/60 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              collapsed && "justify-center px-2"
            )}
          >
            {collapsed ? (
              <ChevronsRight className="size-4 shrink-0" />
            ) : (
              <>
                <ChevronsLeft className="size-4 shrink-0" />
                <span>Collapse</span>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
