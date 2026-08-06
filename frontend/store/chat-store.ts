import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { ChatMessage } from "@/types/chat";

export interface ChatSession {
  id: string; // real backend session_id, once assigned by the first response
  copilotId: string;
  title: string;
  messages: ChatMessage[];
  updatedAt: string;
}

interface ChatState {
  /** All sessions across all copilots, newest first within each copilot. */
  sessions: ChatSession[];
  activeSessionIdByCopilot: Record<string, string | undefined>;
  createDraftSession: (copilotId: string) => string;
  setActiveSession: (copilotId: string, sessionId: string) => void;
  renameSessionIfUntitled: (sessionId: string, title: string) => void;
  assignRealSessionId: (draftId: string, realId: string) => void;
  appendMessage: (sessionId: string, message: ChatMessage) => void;
  updateMessage: (sessionId: string, messageId: string, patch: Partial<ChatMessage>) => void;
  appendToMessageContent: (sessionId: string, messageId: string, delta: string) => void;
  deleteSession: (sessionId: string) => void;
}

function makeId() {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `id-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      sessions: [],
      activeSessionIdByCopilot: {},

      createDraftSession: (copilotId) => {
        const draftId = `draft-${makeId()}`;
        const session: ChatSession = {
          id: draftId,
          copilotId,
          title: "New conversation",
          messages: [],
          updatedAt: new Date().toISOString(),
        };
        set((state) => ({
          sessions: [session, ...state.sessions],
          activeSessionIdByCopilot: {
            ...state.activeSessionIdByCopilot,
            [copilotId]: draftId,
          },
        }));
        return draftId;
      },

      setActiveSession: (copilotId, sessionId) =>
        set((state) => ({
          activeSessionIdByCopilot: { ...state.activeSessionIdByCopilot, [copilotId]: sessionId },
        })),

      renameSessionIfUntitled: (sessionId, title) =>
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId && s.title === "New conversation"
              ? { ...s, title: title.slice(0, 60) }
              : s
          ),
        })),

      // A session starts under a client-generated "draft-..." id (before
      // the backend has assigned one) and is renamed to the real
      // session_id once the first response arrives -- so refreshing the
      // page and picking up right where the backend's own memory would
      // resume correctly if the history-fetch endpoint is added later.
      assignRealSessionId: (draftId, realId) =>
        set((state) => {
          const activeEntries = Object.entries(state.activeSessionIdByCopilot).map(
            ([copilotId, sid]) => [copilotId, sid === draftId ? realId : sid] as const
          );
          return {
            sessions: state.sessions.map((s) => (s.id === draftId ? { ...s, id: realId } : s)),
            activeSessionIdByCopilot: Object.fromEntries(activeEntries),
          };
        }),

      appendMessage: (sessionId, message) =>
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? { ...s, messages: [...s.messages, message], updatedAt: new Date().toISOString() }
              : s
          ),
        })),

      updateMessage: (sessionId, messageId, patch) =>
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? {
                  ...s,
                  messages: s.messages.map((m) => (m.id === messageId ? { ...m, ...patch } : m)),
                }
              : s
          ),
        })),

      appendToMessageContent: (sessionId, messageId, delta) =>
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? {
                  ...s,
                  messages: s.messages.map((m) =>
                    m.id === messageId ? { ...m, content: m.content + delta } : m
                  ),
                }
              : s
          ),
        })),

      deleteSession: (sessionId) =>
        set((state) => ({
          sessions: state.sessions.filter((s) => s.id !== sessionId),
        })),
    }),
    { name: "ecs-chat-sessions" }
  )
);

export function useCopilotSessions(copilotId: string) {
  return useChatStore((s) => s.sessions.filter((session) => session.copilotId === copilotId));
}
