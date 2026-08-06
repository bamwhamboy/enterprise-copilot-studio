import { API_BASE_URL, apiClient } from "@/services/api-client";
import { getAuthState } from "@/store/auth-store";
import type {
  ApiDocument,
  ApiKnowledgeSource,
  KnowledgeSourceCreatePayload,
} from "@/types/knowledge-source";

/**
 * Real upload progress requires XMLHttpRequest -- fetch() has no upload
 * progress event. Everything else in this module uses the standard
 * apiClient; this is the one deliberate exception.
 */
function uploadDocumentWithProgress(
  knowledgeSourceId: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<ApiDocument> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("knowledge_source_id", knowledgeSourceId);
    formData.append("file", file);

    xhr.open("POST", `${API_BASE_URL}/documents/upload`);
    const { accessToken } = getAuthState();
    if (accessToken) xhr.setRequestHeader("Authorization", `Bearer ${accessToken}`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject({ status: xhr.status, message: "Malformed response from server." });
        }
      } else {
        let message = "Upload failed.";
        try {
          const body = JSON.parse(xhr.responseText);
          if (typeof body?.detail === "string") message = body.detail;
        } catch {
          // keep default message
        }
        reject({ status: xhr.status, message });
      }
    };
    xhr.onerror = () => reject({ status: 0, message: "Network error during upload." });
    xhr.send(formData);
  });
}

export const knowledgeSourcesApi = {
  list: () => apiClient.get<ApiKnowledgeSource[]>("/knowledge-sources"),
  get: (id: string) => apiClient.get<ApiKnowledgeSource>(`/knowledge-sources/${id}`),
  create: (payload: KnowledgeSourceCreatePayload) =>
    apiClient.post<ApiKnowledgeSource>("/knowledge-sources", payload),
  remove: (id: string) => apiClient.delete<void>(`/knowledge-sources/${id}`),
  uploadDocument: uploadDocumentWithProgress,
  indexDocument: (documentId: string) =>
    apiClient.post<{ document_id: string; chunks_indexed: number; index_status: string }>(
      `/index/${documentId}`
    ),
};
