export interface Citation {
  document_name: string;
  // V2: Fix #2A/#2C -- the backend's Citation model has carried a stable
  // document_id since Fix #2A (app/knowledge_engine/models.py). Optional
  // here (not required) so any citation constructed before this field
  // existed still type-checks -- purely additive.
  document_id?: string | null;
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
  // V2: Fix #2B/#2C -- explicit document scope. Optional; omitted (not
  // sent as null) by buildChatRequestPayload() in lib/api/chat.ts when no
  // document is selected, preserving today's unscoped-chat payload shape
  // exactly for every existing caller.
  document_id?: string | null;
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
