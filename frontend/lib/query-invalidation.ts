import type { QueryClient } from "@tanstack/react-query";

/**
 * Shared invalidation helpers, used by every mutation that touches
 * knowledge sources/documents/copilots -- so every call site invalidates
 * the *whole* related family of query keys consistently, not just the
 * one query the page currently happens to be looking at.
 *
 * This directly fixes a real, confirmed bug: uploading a document (on
 * the Knowledge Source detail page) previously only invalidated that
 * detail query, never the "knowledge-sources" list (Dashboard,
 * Knowledge Sources page) or "documents" list (Documents page) -- so
 * navigating back showed stale counts until those queries' unrelated
 * staleTime eventually expired.
 *
 * invalidateQueries matches by key *prefix* by default (e.g.
 * ["documents"] matches ["documents", sourceFilter, page] for every
 * filter/page combination), which is what makes a single call here
 * enough regardless of which specific filtered/paginated queries are
 * currently mounted elsewhere in the app.
 */
export function invalidateKnowledgeData(queryClient: QueryClient, knowledgeSourceId?: string) {
  queryClient.invalidateQueries({ queryKey: ["knowledge-sources"] });
  queryClient.invalidateQueries({ queryKey: ["documents"] });
  if (knowledgeSourceId) {
    queryClient.invalidateQueries({ queryKey: ["knowledge-source", knowledgeSourceId] });
  }
  // A copilot's own cached record embeds a snapshot of its linked
  // knowledge sources -- keep that in sync too.
  queryClient.invalidateQueries({ queryKey: ["copilots"] });
}

export function invalidateCopilotData(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: ["copilots"] });
}
