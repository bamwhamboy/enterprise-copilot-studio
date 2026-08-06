import { apiClient } from "@/services/api-client";
import type { ApiDocument } from "@/types/knowledge-source";

export interface ListDocumentsParams {
  knowledge_source_id?: string;
  offset?: number;
  limit?: number;
}

function buildQuery(params: ListDocumentsParams): string {
  const search = new URLSearchParams();
  if (params.knowledge_source_id) search.set("knowledge_source_id", params.knowledge_source_id);
  search.set("offset", String(params.offset ?? 0));
  search.set("limit", String(params.limit ?? 100));
  return search.toString();
}

export const documentsApi = {
  list: (params: ListDocumentsParams = {}) =>
    apiClient.get<ApiDocument[]>(`/documents?${buildQuery(params)}`),
  get: (id: string) => apiClient.get<ApiDocument>(`/documents/${id}`),
  remove: (id: string) => apiClient.delete<void>(`/documents/${id}`),
};
