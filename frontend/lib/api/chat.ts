import { API_BASE_URL, apiClient, refreshAccessToken } from "@/services/api-client";
import { getAuthState, useAuthStore } from "@/store/auth-store";
import type { ChatRequestPayload, ChatResponse, ChatStreamDone } from "@/types/chat";

export interface ChatStreamHandlers {
  onChunk: (delta: string) => void;
  onDone: (data: ChatStreamDone) => void;
  onError: (message: string) => void;
}

export interface BuildChatRequestPayloadArgs {
  copilotId: string;
  message: string;
  sessionId?: string;
  /** Fix #2C: explicit document scope, e.g. from a "Chat with this
   * document" link. Falsy (undefined/null/"") omits document_id from the
   * payload entirely -- not sent as null -- so unscoped chat is byte-for-
   * byte identical to before this field existed. */
  documentId?: string | null;
}

/** Builds the /chat and /chat/stream request payload. Pulled out as a pure
 * function (rather than inlined in ChatWorkspace) so document-scope
 * inclusion/omission is unit-testable without rendering React. */
export function buildChatRequestPayload({
  copilotId,
  message,
  sessionId,
  documentId,
}: BuildChatRequestPayloadArgs): ChatRequestPayload {
  return {
    copilot_id: copilotId,
    session_id: sessionId,
    message,
    ...(documentId ? { document_id: documentId } : {}),
  };
}

/** Generic, non-backend-derived message shown when the session can't be
 * silently recovered -- never the raw 401 body ("Could not validate
 * credentials"), which would otherwise read like an assistant reply. */
const SESSION_EXPIRED_MESSAGE = "Your session has expired. Please log in again.";

function isAbortError(err: unknown): boolean {
  return err instanceof Error && err.name === "AbortError";
}

/** One raw POST to /chat/stream with the given access token. Throws on
 * network failure (including AbortError, left for the caller to check). */
function postChatStream(
  payload: ChatRequestPayload,
  accessToken: string | null,
  signal?: AbortSignal
): Promise<Response> {
  return fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify(payload),
    signal,
  });
}

/** Same "log the user out and send them to /login" convention
 * services/api-client.ts uses once refresh is exhausted -- kept identical
 * here so the two request paths fail the same way. */
function endSessionAsExpired(handlers: ChatStreamHandlers) {
  useAuthStore.getState().logout();
  handlers.onError(SESSION_EXPIRED_MESSAGE);
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

/**
 * Consumes the backend's real SSE stream (POST /chat/stream).
 *
 * EventSource can't be used here -- it only supports GET with no custom
 * headers, and this endpoint needs POST + a JSON body + a Bearer token.
 * So this parses the "event: ...\ndata: ...\n\n" frames manually from
 * the raw fetch ReadableStream, matching exactly what
 * app/api/v1/chat.py's StreamingResponse writes.
 *
 * Unlike services/api-client.ts's `request()`, this can't reuse fetch's
 * response body twice, so it drives the same refresh-once-and-retry flow
 * (via the exported `refreshAccessToken()`) by hand: on a 401, refresh,
 * retry exactly once with the new token, and only fall back to ending
 * the session if the refresh fails or the retry is also unauthorized.
 * Any other status (5xx, etc.) is left untouched -- no refresh attempt.
 */
export async function streamChat(
  payload: ChatRequestPayload,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal
): Promise<void> {
  const { accessToken } = getAuthState();

  let res: Response;
  try {
    res = await postChatStream(payload, accessToken, signal);
  } catch (err) {
    if (isAbortError(err)) return;
    handlers.onError("Could not reach the server.");
    return;
  }

  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (!newToken) {
      endSessionAsExpired(handlers);
      return;
    }

    try {
      res = await postChatStream(payload, newToken, signal);
    } catch (err) {
      if (isAbortError(err)) return;
      handlers.onError("Could not reach the server.");
      return;
    }

    if (res.status === 401) {
      // Retried exactly once with a freshly refreshed token and still
      // unauthorized -- stop here rather than looping.
      endSessionAsExpired(handlers);
      return;
    }
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
