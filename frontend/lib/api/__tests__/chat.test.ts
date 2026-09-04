import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { buildChatRequestPayload, streamChat, type ChatStreamHandlers } from "@/lib/api/chat";
import { useAuthStore } from "@/store/auth-store";
import type { ChatRequestPayload } from "@/types/chat";

/**
 * Regression tests for the Finding-4 fix: streamChat() previously bypassed
 * services/api-client.ts's 401 refresh-and-retry flow entirely (raw fetch,
 * no refresh call), which surfaced the backend's raw "Could not validate
 * credentials" 401 body as if it were an assistant reply once the access
 * token expired. These tests exercise the real, unmodified refreshAccessToken()
 * from services/api-client.ts (mocked only at the fetch boundary) to confirm
 * streamChat now reuses that same flow rather than a second implementation.
 */

const CHAT_STREAM_URL = "http://localhost:8000/api/v1/chat/stream";
const REFRESH_URL = "http://localhost:8000/api/v1/auth/refresh";

const PAYLOAD: ChatRequestPayload = {
  copilot_id: "copilot-1",
  session_id: "session-1",
  message: "What is the total annual contract value?",
};

const ORIGINAL_ACCESS_TOKEN = "expired-access-token-do-not-leak";
const REFRESHED_ACCESS_TOKEN = "fresh-access-token-do-not-leak";
const REFRESH_TOKEN = "refresh-token-do-not-leak";

function sseResponse(events: Array<{ event: string; data: unknown }>, status = 200): Response {
  const encoder = new TextEncoder();
  const body = events
    .map((e) => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`)
    .join("");
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode(body));
      controller.close();
    },
  });
  return new Response(stream, { status });
}

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Mirrors real fetch's abort behavior: never settles until the signal fires. */
function pendingUntilAbort(signal: AbortSignal | null | undefined): Promise<Response> {
  return new Promise((_resolve, reject) => {
    signal?.addEventListener("abort", () => {
      reject(new DOMException("The operation was aborted.", "AbortError"));
    });
  });
}

function makeHandlers(): ChatStreamHandlers {
  return { onChunk: vi.fn(), onDone: vi.fn(), onError: vi.fn() };
}

function authHeader(init: RequestInit | undefined): string | undefined {
  return (init?.headers as Record<string, string> | undefined)?.Authorization;
}

describe("streamChat", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: ORIGINAL_ACCESS_TOKEN,
      refreshToken: REFRESH_TOKEN,
      user: null,
      rememberMe: true,
      hasHydrated: true,
    });
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("1. valid access token: sends the request once and streams normally", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url) === CHAT_STREAM_URL) {
        return sseResponse([
          { event: "chunk", data: { delta: "The answer is " } },
          { event: "chunk", data: { delta: "42." } },
          {
            event: "done",
            data: {
              session_id: "session-1",
              message: "The answer is 42.",
              citations: [],
              confidence: 0.7,
            },
          },
        ]);
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });

    const handlers = makeHandlers();
    await streamChat(PAYLOAD, handlers);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(authHeader(fetchMock.mock.calls[0][1])).toBe(`Bearer ${ORIGINAL_ACCESS_TOKEN}`);
    expect(handlers.onChunk).toHaveBeenNthCalledWith(1, "The answer is ");
    expect(handlers.onChunk).toHaveBeenNthCalledWith(2, "42.");
    expect(handlers.onDone).toHaveBeenCalledTimes(1);
    expect(handlers.onError).not.toHaveBeenCalled();
  });

  it("2. expired token: refreshes once, retries once, and streams the retried response", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    let chatCallCount = 0;
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (String(url) === CHAT_STREAM_URL) {
        chatCallCount += 1;
        if (chatCallCount === 1) {
          expect(authHeader(init)).toBe(`Bearer ${ORIGINAL_ACCESS_TOKEN}`);
          return jsonResponse({ detail: "Could not validate credentials" }, 401);
        }
        expect(authHeader(init)).toBe(`Bearer ${REFRESHED_ACCESS_TOKEN}`);
        return sseResponse([
          {
            event: "done",
            data: { session_id: "session-1", message: "ok", citations: [], confidence: 0.6 },
          },
        ]);
      }
      if (String(url) === REFRESH_URL) {
        return jsonResponse(
          {
            access_token: REFRESHED_ACCESS_TOKEN,
            refresh_token: REFRESH_TOKEN,
            token_type: "bearer",
            expires_in: 1800,
          },
          200
        );
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });

    const handlers = makeHandlers();
    await streamChat(PAYLOAD, handlers);

    expect(chatCallCount).toBe(2);
    expect(fetchMock).toHaveBeenCalledTimes(3); // chat/stream, auth/refresh, chat/stream retry
    expect(handlers.onDone).toHaveBeenCalledTimes(1);
    expect(handlers.onError).not.toHaveBeenCalled();
    expect(useAuthStore.getState().accessToken).toBe(REFRESHED_ACCESS_TOKEN);
  });

  it("3. refresh failure: attempts no second chat request and returns a clear session error", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url) === CHAT_STREAM_URL) {
        return jsonResponse({ detail: "Could not validate credentials" }, 401);
      }
      if (String(url) === REFRESH_URL) {
        return jsonResponse({ detail: "Invalid refresh token" }, 401);
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });

    const handlers = makeHandlers();
    await streamChat(PAYLOAD, handlers);

    const chatCalls = fetchMock.mock.calls.filter(([url]) => String(url) === CHAT_STREAM_URL);
    expect(chatCalls).toHaveLength(1);
    expect(handlers.onError).toHaveBeenCalledTimes(1);
    const [message] = (handlers.onError as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(message).toBe("Your session has expired. Please log in again.");
    expect(message).not.toContain("Could not validate credentials");
    expect(useAuthStore.getState().accessToken).toBeNull();
  });

  it("4. retry still 401: stops after exactly one retry with no further attempts", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    let chatCallCount = 0;
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url) === CHAT_STREAM_URL) {
        chatCallCount += 1;
        return jsonResponse({ detail: "Could not validate credentials" }, 401);
      }
      if (String(url) === REFRESH_URL) {
        return jsonResponse(
          {
            access_token: REFRESHED_ACCESS_TOKEN,
            refresh_token: REFRESH_TOKEN,
            token_type: "bearer",
            expires_in: 1800,
          },
          200
        );
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });

    const handlers = makeHandlers();
    await streamChat(PAYLOAD, handlers);

    expect(chatCallCount).toBe(2); // original + exactly one retry, never a third
    expect(handlers.onError).toHaveBeenCalledTimes(1);
    expect((handlers.onError as ReturnType<typeof vi.fn>).mock.calls[0][0]).toBe(
      "Your session has expired. Please log in again."
    );
    expect(useAuthStore.getState().accessToken).toBeNull();
  });

  it("5. non-401 streaming error: leaves the existing behavior intact, no refresh attempted", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url) === CHAT_STREAM_URL) {
        return jsonResponse({ detail: "Internal server error" }, 500);
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });

    const handlers = makeHandlers();
    await streamChat(PAYLOAD, handlers);

    const refreshCalls = fetchMock.mock.calls.filter(([url]) => String(url) === REFRESH_URL);
    expect(refreshCalls).toHaveLength(0);
    expect(handlers.onError).toHaveBeenCalledWith("Internal server error");
    expect(useAuthStore.getState().accessToken).toBe(ORIGINAL_ACCESS_TOKEN);
  });

  it("6. cancellation: aborting mid-request resolves silently with no handler firing", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (String(url) === CHAT_STREAM_URL) {
        return pendingUntilAbort(init?.signal);
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });

    const handlers = makeHandlers();
    const controller = new AbortController();
    const promise = streamChat(PAYLOAD, handlers, controller.signal);
    controller.abort();
    await promise;

    expect(handlers.onChunk).not.toHaveBeenCalled();
    expect(handlers.onDone).not.toHaveBeenCalled();
    expect(handlers.onError).not.toHaveBeenCalled();
  });

  it("7. security: access/refresh tokens never appear in a handler-facing message", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url) === CHAT_STREAM_URL) {
        return jsonResponse({ detail: "Could not validate credentials" }, 401);
      }
      if (String(url) === REFRESH_URL) {
        return jsonResponse({ detail: "Invalid refresh token" }, 401);
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });

    const handlers = makeHandlers();
    await streamChat(PAYLOAD, handlers);

    const observedMessages = [
      ...(handlers.onError as ReturnType<typeof vi.fn>).mock.calls.map((c) => String(c[0])),
      ...(handlers.onChunk as ReturnType<typeof vi.fn>).mock.calls.map((c) => String(c[0])),
    ];
    for (const message of observedMessages) {
      expect(message).not.toContain(ORIGINAL_ACCESS_TOKEN);
      expect(message).not.toContain(REFRESHED_ACCESS_TOKEN);
      expect(message).not.toContain(REFRESH_TOKEN);
    }
  });
});

/**
 * Fix #2C: explicit document-scoped chat. buildChatRequestPayload() is the
 * single place ChatWorkspace constructs the /chat(/stream) payload, so
 * document_id inclusion/omission is tested here directly rather than via
 * a full component render (no jsdom/testing-library in this project's
 * Vitest setup -- see vitest.config.ts, "node" environment only).
 */
describe("buildChatRequestPayload", () => {
  it("a/b: includes document_id when a document scope is present", () => {
    const payload = buildChatRequestPayload({
      copilotId: "copilot-1",
      message: "What does this say?",
      sessionId: "session-1",
      documentId: "document-a",
    });

    expect(payload).toEqual({
      copilot_id: "copilot-1",
      session_id: "session-1",
      message: "What does this say?",
      document_id: "document-a",
    });
  });

  it("c: omits document_id entirely (not null) when no document scope is present", () => {
    const payload = buildChatRequestPayload({
      copilotId: "copilot-1",
      message: "What does this say?",
      sessionId: "session-1",
    });

    expect(payload).toEqual({
      copilot_id: "copilot-1",
      session_id: "session-1",
      message: "What does this say?",
    });
    expect("document_id" in payload).toBe(false);
  });

  it("c: omits document_id for explicit undefined/null/empty-string scope alike", () => {
    for (const documentId of [undefined, null, ""] as const) {
      const payload = buildChatRequestPayload({
        copilotId: "copilot-1",
        message: "hi",
        documentId,
      });
      expect("document_id" in payload).toBe(false);
    }
  });

  it("e: existing unscoped-chat shape (no documentId arg at all) is unaffected", () => {
    const payload = buildChatRequestPayload({
      copilotId: "copilot-1",
      message: "hi",
    });
    expect(payload).toEqual({
      copilot_id: "copilot-1",
      session_id: undefined,
      message: "hi",
    });
  });
});
