export type DocumentProcessingStatus = "UPLOADED" | "PROCESSING" | "READY" | "FAILED";
export type DocumentIndexStatus = "NOT_INDEXED" | "INDEXING" | "INDEXED" | "FAILED";

export interface ApiDocument {
  id: string;
  knowledge_source_id: string;
  name: string;
  status: "pending" | "processing" | "indexed";
  pages: number;
  chunks: number;
  embeddings: number;
  original_filename: string | null;
  processing_status: DocumentProcessingStatus | null;
  index_status: DocumentIndexStatus | null;
  created_at: string;
  updated_at: string;
}

export interface ApiKnowledgeSource {
  id: string;
  name: string;
  source_type: "documents" | "database" | "website" | "connector";
  status: "active" | "syncing" | "connected" | "pending" | "coming_soon";
  created_at: string;
  updated_at: string;
  documents: ApiDocument[];
}

export interface KnowledgeSourceCreatePayload {
  name: string;
  source_type?: ApiKnowledgeSource["source_type"];
  status?: ApiKnowledgeSource["status"];
}
