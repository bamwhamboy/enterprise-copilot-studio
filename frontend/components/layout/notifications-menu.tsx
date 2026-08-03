"use client";

import { Bell } from "lucide-react";

import type { NotificationItem } from "@/types/user";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const placeholderNotifications: NotificationItem[] = [
  {
    id: "n1",
    title: "HR Copilot deployed",
    description: "Version 1.2 is live in the production tenant.",
    timestamp: "2h ago",
    read: false,
  },
  {
    id: "n2",
    title: "Knowledge source sync complete",
    description: "Policies_2026.pdf finished re-indexing.",
    timestamp: "5h ago",
    read: false,
  },
  {
    id: "n3",
    title: "Cost threshold notice",
    description: "Monthly spend crossed 80% of the configured budget.",
    timestamp: "1d ago",
    read: true,
  },
];

export function NotificationsMenu() {
  const unreadCount = placeholderNotifications.filter((n) => !n.read).length;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="size-4" />
          {unreadCount > 0 && (
            <span className="absolute right-1.5 top-1.5 flex size-2 rounded-full bg-primary" />
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between text-sm font-semibold text-foreground">
          Notifications
          {unreadCount > 0 && (
            <span className="text-xs font-normal text-muted-foreground">
              {unreadCount} unread
            </span>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <div className="flex flex-col gap-1 py-1">
          {placeholderNotifications.map((n) => (
            <div
              key={n.id}
              className="flex flex-col gap-0.5 rounded-md px-2 py-2 hover:bg-accent"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-foreground">
                  {n.title}
                </span>
                {!n.read && (
                  <span className="size-1.5 shrink-0 rounded-full bg-primary" />
                )}
              </div>
              <span className="text-xs text-muted-foreground">
                {n.description}
              </span>
              <span className="text-[11px] text-muted-foreground/70">
                {n.timestamp}
              </span>
            </div>
          ))}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
