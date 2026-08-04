import { QueryClient } from "@tanstack/react-query";

/**
 * Factory rather than a singleton export, so each request/session
 * (relevant once this ships with SSR + auth) gets an isolated cache.
 */
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
        retry: 1,
      },
      mutations: {
        retry: 0,
      },
    },
  });
}
