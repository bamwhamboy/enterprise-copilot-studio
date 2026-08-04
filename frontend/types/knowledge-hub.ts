import type { LucideIcon } from "lucide-react";

export type KnowledgeHubTab = "documents" | "databases" | "websites" | "connectors";

export interface KnowledgeHubMetric {
  id: string;
  label: string;
  value: string;
  icon: LucideIcon;
}

export type CollectionStatus = "active" | "syncing" | "attention";

export interface KnowledgeCollection {
  id: string;
  name: string;
  documentCount: number;
  status: CollectionStatus;
  lastUpdated: string;
}

export type DocumentStatus = "indexed" | "processing" | "pending";

export interface KnowledgeDocument {
  id: string;
  name: string;
  collectionId: string;
  status: DocumentStatus;
  pages: number;
  chunks: number;
  embeddings: number;
  uploadedAt: string;
}

export type DatabaseStatus = "connected" | "coming-soon";

export interface KnowledgeDatabase {
  id: string;
  name: string;
  engine: string;
  description: string;
  status: DatabaseStatus;
}

export type WebsiteStatus = "indexed" | "pending";

export interface KnowledgeWebsite {
  id: string;
  name: string;
  url: string;
  status: WebsiteStatus;
  lastCrawled: string;
}

export interface EnterpriseConnector {
  id: string;
  name: string;
  icon: LucideIcon;
}

export interface KnowledgeStatItem {
  id: string;
  label: string;
  value: string;
}

export interface KnowledgeConfigItem {
  id: string;
  label: string;
  value: string;
  icon: LucideIcon;
}
