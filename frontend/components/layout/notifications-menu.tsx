"use client";

import { Bell } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

/**
 * There is no backend endpoint for notifications -- this previously
 * showed a hardcoded, fake notification list with a fake "unread"
 * badge, which looked like a live feature but wasn't connected to
 * anything real. Rather than fabricate data, this shows an honest
 * empty state until a real notifications endpoint exists.
 */
export function NotificationsMenu() {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Notifications">
          <Bell className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="text-sm font-semibold text-foreground">
          Notifications
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <p className="px-2 py-6 text-center text-xs text-muted-foreground">
          Notifications aren&apos;t connected to live data yet.
        </p>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
