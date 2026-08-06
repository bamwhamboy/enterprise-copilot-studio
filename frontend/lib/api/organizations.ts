import { apiClient } from "@/services/api-client";
import type { OrganizationRead } from "@/types/auth";

export const organizationsApi = {
  list: () => apiClient.get<OrganizationRead[]>("/organizations"),
};
