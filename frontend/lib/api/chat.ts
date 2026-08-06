import { API_BASE_URL, apiClient } from "@/services/api-client";
import { getAuthState } from "@/store/auth-store";
import type { ChatRequestPayload, ChatResponse, ChatStreamDone } from "@/types/chat";

export interface ChatStreamHandlers {
  onChunk: (delta: string) => void;
  onDone: (data: ChatStreamDone) => void;
  onError: (message: string) => void;
}

/**
 * Consumes the backend's real SSE stream (POST /chat/stream).
 *
 * EventSource can't be used here -- it only supports GET with no custom
 * headers, and this endpoint needs POST + a JSON body + a Bearer token.
 * So this parses the "event: ...\ndata: ...\n\n" frames manually from
 * the raw fetch ReadableStream, matching exactly what
 * app/api/v1/chat.py's StreamingResponse writes.
 */
export async function streamChat(
  payload: ChatRequestPayload,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal
): Promise<void> {
  const { accessToken } = getAuthState();

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") return;
    handlers.onError("Could not reach the server.");
    return;
  }

  if (!res.ok || !res.body) {
    let message = "Failed to start the chat stream.";
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") message = data.detail;
    } catch {
      // keep default message
    }
    handlers.onError(message);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      parseFrame(buffer.slice(0, boundary), handlers);
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
    }
  }
}

function parseFrame(rawFrame: string, handlers: ChatStreamHandlers) {
  let event = "message";
  let data = "";
  for (const line of rawFrame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice("event:".length).trim();
    else if (line.startsWith("data:")) data += line.slice("data:".length).trim();
  }
  if (!data) return;

  try {
    const parsed = JSON.parse(data);
    if (event === "chunk") handlers.onChunk(parsed.delta ?? "");
    else if (event === "done") handlers.onDone(parsed as ChatStreamDone);
    else if (event === "error") handlers.onError(parsed.message ?? "The assistant hit an error.");
  } catch {
    // Malformed frame -- skip rather than crash the stream.
  }
}

/** Non-streaming fallback (POST /chat), used only if streaming setup fails outright. */
export function sendChatMessage(payload: ChatRequestPayload): Promise<ChatResponse> {
  return apiClient.post<ChatResponse>("/chat", payload);
}
