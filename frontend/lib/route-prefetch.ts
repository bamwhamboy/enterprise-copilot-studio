import type { QueryClient } from "@tanstack/react-query";

import { copilotsApi } from "@/lib/api/copilots";
import { knowledgeSourcesApi } from "@/lib/api/knowledge-sources";
import { documentsApi } from "@/lib/api/documents";
import { organizationsApi } from "@/lib/api/organizations";

/**
 * Maps a sidebar route to the queries it needs, so hovering a nav link
 * can start fetching before the click even lands -- by the time
 * navigation actually completes, the page frequently has its data
 * already cached instead of showing its own loading skeleton.
 *
 * Deliberately keyed by exact route prefix rather than trying to be
 * clever about matching dynamic segments; only the routes with a real
 * top-level data dependency are listed; anything else (Marketplace,
 * the various "Coming Soon" pages) has nothing worth prefetching.
 */
export function prefetchForRoute(queryClient: QueryClient, href: string) {
  switch (href) {
    case "/":
      queryClient.prefetchQuery({ queryKey: ["copilots"], queryFn: copilotsApi.list });
      queryClient.prefetchQuery({
        queryKey: ["knowledge-sources"],
        queryFn: knowledgeSourcesApi.list,
      });
      queryClient.prefetchQuery({
        queryKey: ["organizations"],
        queryFn: organizationsApi.list,
      });
      break;
    case "/copilots":
      queryClient.prefetchQuery({ queryKey: ["copilots"], queryFn: copilotsApi.list });
      queryClient.prefetchQuery({
        queryKey: ["knowledge-sources"],
        queryFn: knowledgeSourcesApi.list,
      });
      break;
    case "/knowledge-sources":
      queryClient.prefetchQuery({
        queryKey: ["knowledge-sources"],
        queryFn: knowledgeSourcesApi.list,
      });
      break;
    case "/documents":
      queryClient.prefetchQuery({
        queryKey: ["documents", "all", 0],
        queryFn: () => documentsApi.list({ offset: 0, limit: 10 }),
      });
      queryClient.prefetchQuery({
        queryKey: ["knowledge-sources"],
        queryFn: knowledgeSourcesApi.list,
      });
      break;
    case "/settings":
      queryClient.prefetchQuery({
        queryKey: ["organizations"],
        queryFn: organizationsApi.list,
      });
      queryClient.prefetchQuery({ queryKey: ["copilots"], queryFn: copilotsApi.list });
      break;
    default:
      break;
  }
}
