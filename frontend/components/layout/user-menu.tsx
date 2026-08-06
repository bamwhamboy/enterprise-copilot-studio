"use client";

import { LogOut, Settings, UserRound } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { useAuthStore } from "@/store/auth-store";
import { useChatStore } from "@/store/chat-store";
import { logoutRequest } from "@/lib/api/auth";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import Link from "next/link";

function getInitials(name: string) {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function UserMenu() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const refreshToken = useAuthStore((s) => s.refreshToken);
  const logout = useAuthStore((s) => s.logout);

  const displayName = user?.full_name || user?.email || "Loading…";
  const initials = getInitials(user?.full_name || user?.email || "?");

  async function handleSignOut() {
    if (refreshToken) {
      // Best-effort — revoke server-side, but never block the client-side
      // sign-out on it (e.g. if the token's already expired/revoked).
      logoutRequest(refreshToken).catch(() => {});
    }
    // Clear every cached query -- AuthGuard lives in the root layout and
    // never unmounts, so without this, a *different* user logging in on
    // the same browser could briefly see this user's cached data.
    queryClient.clear();
    // Chat sessions persist to localStorage independently of the auth
    // store (so history survives a refresh) -- which means without this,
    // they'd also survive a *logout*, and a different user signing in on
    // the same browser would see the previous user's conversations.
    useChatStore.persist.clearStorage();
    logout();
    // A hard navigation here is deliberate, not an oversight: relying on
    // AuthGuard's reactive redirect (an effect responding to accessToken
    // becoming null) means React has to reconcile the entire
    // authenticated tree away client-side, which is exactly the kind of
    // transition that produced a blank-screen flash. A full navigation
    // sidesteps that reconciliation entirely and guarantees a completely
    // clean slate -- arguably the correct behavior for "log out" anyway.
    window.location.href = "/login";
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex items-center gap-2 rounded-full outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring">
          <Avatar>
            <AvatarFallback className="bg-primary/10 text-primary">
              {initials}
            </AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel className="flex flex-col gap-0.5">
          <span className="text-sm font-semibold text-foreground">
            {displayName}
          </span>
          <span className="text-xs font-normal text-muted-foreground">
            {user?.email}
          </span>
          {user?.role && (
            <span className="mt-1 inline-flex w-fit items-center rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium capitalize text-primary">
              {user.role.name.replace(/_/g, " ")}
            </span>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/settings">
            <UserRound />
            Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/settings">
            <Settings />
            Settings
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive" onSelect={handleSignOut}>
          <LogOut />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
