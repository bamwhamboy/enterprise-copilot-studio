export interface Citation {
  document_name: string;
  knowledge_source_id: string;
  page_number: number | null;
  section: string | null;
  chunk_number: number;
  score: number | null;
}

export interface ChatRequestPayload {
  copilot_id: string;
  session_id?: string | null;
  message: string;
  knowledge_source_id?: string | null;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  citations: Citation[];
  confidence: number;
}

/** SSE "done" event payload (app/api/v1/chat.py's /chat/stream). */
export interface ChatStreamDone {
  session_id: string;
  message: string;
  citations: Citation[];
  confidence: number;
}

export type ChatMessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  citations?: Citation[];
  confidence?: number;
  isStreaming?: boolean;
  createdAt: string;
}
