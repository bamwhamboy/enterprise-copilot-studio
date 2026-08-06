"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuthStore } from "@/store/auth-store";
import { fetchCurrentUser } from "@/lib/api/auth";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Wraps every authenticated route. Redirects to /login if there's no
 * access token once the persisted auth store has rehydrated, and
 * refreshes the current-user profile from the real backend (not just
 * trusting a possibly-stale cached value) before rendering children.
 *
 * This is the single place that redirects to /login when unauthenticated
 * -- nothing else (e.g. the logout button) should also call
 * router.push/replace("/login") directly. Two independent navigations
 * to the same destination racing each other was a real source of
 * glitchy/blank transitions on logout.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const hasHydrated = useAuthStore((s) => s.hasHydrated);
  const accessToken = useAuthStore((s) => s.accessToken);
  const setUser = useAuthStore((s) => s.setUser);
  const logout = useAuthStore((s) => s.logout);

  const {
    data: user,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["me"],
    queryFn: fetchCurrentUser,
    enabled: hasHydrated && Boolean(accessToken),
    retry: false,
  });

  useEffect(() => {
    if (user) setUser(user);
  }, [user, setUser]);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace("/login");
    }
  }, [hasHydrated, accessToken, router]);

  useEffect(() => {
    // The "me" check failed even after api-client's automatic one-shot
    // refresh attempt (services/api-client.ts) -- the session is
    // genuinely dead (expired/revoked refresh token). Force a clean
    // logout instead of leaving the app in a stuck, half-authenticated
    // state with a token that will never successfully verify.
    if (hasHydrated && accessToken && isError) {
      queryClient.clear();
      logout();
    }
  }, [hasHydrated, accessToken, isError, logout, queryClient]);

  if (!hasHydrated || !accessToken || (isLoading && !user)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-[#5b7cfa] shadow-lg shadow-primary/25">
            <span className="text-lg font-bold text-primary-foreground">E</span>
          </div>
          <Skeleton className="h-2 w-32 rounded-full" />
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
