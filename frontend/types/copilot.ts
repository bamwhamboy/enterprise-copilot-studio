export type CopilotDomain =
  | "hr"
  | "finance"
  | "procurement"
  | "sales"
  | "legal"
  | "it"
  | "analytics";

export type CopilotStatus = "draft" | "active" | "archived";

export interface KnowledgeSourceSummary {
  id: string;
  name: string;
  source_type: "documents" | "database" | "website" | "connector";
  status: "active" | "syncing" | "connected" | "pending" | "coming_soon";
}

export interface Copilot {
  id: string;
  name: string;
  description: string | null;
  domain: CopilotDomain;
  status: CopilotStatus;
  model: string;
  created_at: string;
  updated_at: string;
  knowledge_sources: KnowledgeSourceSummary[];
}

export interface CopilotCreatePayload {
  name: string;
  description?: string | null;
  domain?: CopilotDomain;
  status?: CopilotStatus;
  model?: string;
  knowledge_source_ids?: string[];
}

export type CopilotUpdatePayload = Partial<CopilotCreatePayload>;

export const COPILOT_DOMAIN_LABELS: Record<CopilotDomain, string> = {
  hr: "HR",
  finance: "Finance",
  procurement: "Procurement",
  sales: "Sales",
  legal: "Legal",
  it: "IT",
  analytics: "Analytics",
};

export const COPILOT_STATUS_LABELS: Record<CopilotStatus, string> = {
  draft: "Draft",
  active: "Active",
  archived: "Archived",
};
