import { apiClient } from "@/services/api-client";
import type { Copilot, CopilotCreatePayload, CopilotUpdatePayload } from "@/types/copilot";

export const copilotsApi = {
  list: () => apiClient.get<Copilot[]>("/copilots"),
  get: (id: string) => apiClient.get<Copilot>(`/copilots/${id}`),
  create: (payload: CopilotCreatePayload) => apiClient.post<Copilot>("/copilots", payload),
  update: (id: string, payload: CopilotUpdatePayload) =>
    apiClient.put<Copilot>(`/copilots/${id}`, payload),
  remove: (id: string) => apiClient.delete<void>(`/copilots/${id}`),
};
