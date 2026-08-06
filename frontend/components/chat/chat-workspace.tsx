"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Database } from "lucide-react";

import { copilotsApi } from "@/lib/api/copilots";
import { streamChat } from "@/lib/api/chat";
import { checkHealth } from "@/lib/api/health";
import { useAuthStore } from "@/store/auth-store";
import { useChatStore, useCopilotSessions } from "@/store/chat-store";
import type { ChatMessage } from "@/types/chat";
import { COPILOT_DOMAIN_LABELS, type Copilot } from "@/types/copilot";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ModelBadge } from "@/components/chat/model-badge";
import { ConversationList } from "@/components/chat/conversation-list";
import { MessageList } from "@/components/chat/message-list";
import { CopilotWarmingUp } from "@/components/chat/copilot-warming-up";
import { MessageErrorBoundary } from "@/components/chat/message-error-boundary";
import { SuggestedPrompts } from "@/components/chat/suggested-prompts";
import { ChatInput } from "@/components/chat/chat-input";

const SUGGESTED_PROMPTS = [
  "What does our policy say about this topic?",
  "Summarize the key points from the linked knowledge sources.",
  "What documents are you grounded in right now?",
  "Explain this in simpler terms for a new employee.",
];

function makeId() {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `id-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function getInitials(name: string) {
  return name
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function ChatWorkspace({ copilotId }: { copilotId: string }) {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);

  const queryClient = useQueryClient();
  const { data: copilot, isLoading: isCopilotLoading } = useQuery({
    queryKey: ["copilot", copilotId],
    queryFn: () => copilotsApi.get(copilotId),
    initialData: () =>
      queryClient.getQueryData<Copilot[]>(["copilots"])?.find((c) => c.id === copilotId),
    // The seeded value came from the list endpoint, not this specific
    // detail fetch -- treat it as immediately stale so a real fetch
    // still happens in the background to catch anything the list
    // response might not include, without blocking the initial paint.
    initialDataUpdatedAt: 0,
  });

  const sessions = useCopilotSessions(copilotId);
  const activeSessionId = useChatStore((s) => s.activeSessionIdByCopilot[copilotId]);
  const createDraftSession = useChatStore((s) => s.createDraftSession);
  const setActiveSession = useChatStore((s) => s.setActiveSession);
  const renameSessionIfUntitled = useChatStore((s) => s.renameSessionIfUntitled);
  const assignRealSessionId = useChatStore((s) => s.assignRealSessionId);
  const appendMessage = useChatStore((s) => s.appendMessage);
  const updateMessage = useChatStore((s) => s.updateMessage);
  const appendToMessageContent = useChatStore((s) => s.appendToMessageContent);
  const deleteSession = useChatStore((s) => s.deleteSession);

  const activeSession = sessions.find((s) => s.id === activeSessionId);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const streamingMessageRef = useRef<{ sessionId: string; messageId: string } | null>(null);

  const finalizeAbortedMessage = useCallback(() => {
    const target = streamingMessageRef.current;
    if (target) {
      updateMessage(target.sessionId, target.messageId, {
        content: "Generation stopped.",
        isStreaming: false,
      });
      streamingMessageRef.current = null;
    }
  }, [updateMessage]);

  // Fire a lightweight, fire-and-forget request the moment the chat
  // opens, before the user has typed anything. This can't reduce the
  // backend's own LLM/retrieval latency (no endpoint exists for that,
  // and this sprint intentionally doesn't add backend endpoints for a
  // frontend polish pass) -- but it does mean any idle connection pool
  // or lazy-initialized backend resource gets touched during the
  // "reading the welcome screen" moment rather than during the first
  // real query, which is exactly when a cold-start delay is most
  // noticeable.
  useEffect(() => {
    checkHealth();
  }, []);

  // Cancel any in-flight generation when the user navigates away from
  // this copilot's chat entirely (not just switching conversations
  // within it). Previously nothing aborted the fetch on unmount, so a
  // response kept generating in the background -- wasted work, and not
  // what "leave chat while generating" should do.
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      finalizeAbortedMessage();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Ensure there's always an active (possibly empty) session once sessions load.
  useEffect(() => {
    if (!activeSessionId || !sessions.some((s) => s.id === activeSessionId)) {
      if (sessions.length > 0) {
        setActiveSession(copilotId, sessions[0].id);
      } else {
        createDraftSession(copilotId);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [copilotId, sessions.length]);

  const userInitials = useMemo(
    () => getInitials(user?.full_name || user?.email || "?"),
    [user]
  );

  const runStream = useCallback(
    async (sessionId: string, backendSessionId: string | undefined, text: string) => {
      const assistantId = makeId();
      appendMessage(sessionId, {
        id: assistantId,
        role: "assistant",
        content: "",
        isStreaming: true,
        createdAt: new Date().toISOString(),
      });
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;
      streamingMessageRef.current = { sessionId, messageId: assistantId };

      // Safety net: if neither onDone nor onError ever fires for any
      // reason, this guarantees the UI un-sticks itself rather than
      // staying in a "generating" state forever.
      const safetyTimeout = setTimeout(() => {
        if (streamingMessageRef.current?.messageId === assistantId) {
          controller.abort();
          updateMessage(sessionId, assistantId, {
            content: "This is taking longer than expected. Please try again.",
            isStreaming: false,
          });
          streamingMessageRef.current = null;
          setIsStreaming(false);
        }
      }, 90_000);

      await streamChat(
        {
          copilot_id: copilotId,
          session_id: backendSessionId,
          message: text,
        },
        {
          onChunk: (delta) => appendToMessageContent(sessionId, assistantId, delta),
          onDone: (data) => {
            clearTimeout(safetyTimeout);
            streamingMessageRef.current = null;
            if (sessionId !== data.session_id) {
              assignRealSessionId(sessionId, data.session_id);
            }
            updateMessage(data.session_id, assistantId, {
              content: data.message,
              citations: data.citations,
              confidence: data.confidence,
              isStreaming: false,
            });
            setIsStreaming(false);
          },
          onError: (message) => {
            clearTimeout(safetyTimeout);
            streamingMessageRef.current = null;
            updateMessage(sessionId, assistantId, {
              content: message || "Something went wrong generating a response.",
              isStreaming: false,
            });
            setIsStreaming(false);
          },
        },
        controller.signal
      );
    },
    [copilotId, appendMessage, appendToMessageContent, updateMessage, assignRealSessionId]
  );

  function handleSend(text?: string) {
    const messageText = (text ?? input).trim();
    if (!messageText || isStreaming) return;

    // Defensive recovery: activeSession should always exist (the effect
    // above guarantees it), but if it's ever missing for any reason,
    // create a fresh one rather than silently doing nothing -- a
    // "working" input that doesn't respond is worse than starting a new
    // conversation.
    const session = activeSession ?? sessions.find((s) => s.id === activeSessionId);
    const targetSessionId = session?.id ?? createDraftSession(copilotId);

    setInput("");
    renameSessionIfUntitled(targetSessionId, messageText);
    appendMessage(targetSessionId, {
      id: makeId(),
      role: "user",
      content: messageText,
      createdAt: new Date().toISOString(),
    });

    const backendSessionId = targetSessionId.startsWith("draft-") ? undefined : targetSessionId;
    runStream(targetSessionId, backendSessionId, messageText);
  }

  function handleRegenerate() {
    if (!activeSession || isStreaming) return;
    const lastUser = [...activeSession.messages].reverse().find((m) => m.role === "user");
    if (!lastUser) return;
    const backendSessionId = activeSession.id.startsWith("draft-")
      ? undefined
      : activeSession.id;
    runStream(activeSession.id, backendSessionId, lastUser.content);
  }

  function handleStop() {
    abortRef.current?.abort();
    finalizeAbortedMessage();
    setIsStreaming(false);
  }

  function handleNewConversation() {
    createDraftSession(copilotId);
  }

  if (isCopilotLoading) {
    return <CopilotWarmingUp />;
  }

  if (!copilot) {
    return (
      <div className="flex h-[calc(100vh-6rem)] flex-col items-center justify-center gap-3 text-center">
        <p className="text-sm font-medium text-foreground">Copilot not found.</p>
        <Button variant="outline" onClick={() => router.push("/copilots")}>
          Back to Copilots
        </Button>
      </div>
    );
  }

  const messages: ChatMessage[] = activeSession?.messages ?? [];

  return (
    <div className="grid h-[calc(100vh-6rem)] grid-cols-1 overflow-hidden rounded-2xl border border-border bg-background shadow-sm lg:grid-cols-[240px_1fr]">
      <div className="hidden lg:block">
        <ConversationList
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelect={(id) => setActiveSession(copilotId, id)}
          onNew={handleNewConversation}
          onDelete={(id) => {
            deleteSession(id);
            if (id === activeSessionId) createDraftSession(copilotId);
          }}
        />
      </div>

      <div className="flex min-w-0 flex-col">
        {/* Header */}
        <div className="flex items-center justify-between gap-3 border-b border-border bg-card/60 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="shrink-0"
              onClick={() => router.push("/copilots")}
              aria-label="Back to Copilots"
            >
              <ArrowLeft className="size-4" />
            </Button>
            <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-sm font-semibold text-primary">
              {getInitials(copilot.name)}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-foreground">{copilot.name}</p>
              <p className="truncate text-xs text-muted-foreground">
                {COPILOT_DOMAIN_LABELS[copilot.domain]} copilot
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <ModelBadge model={copilot.model} />
            {copilot.knowledge_sources.length > 0 && (
              <span
                className="hidden items-center gap-1.5 rounded-full border border-border bg-muted/60 px-2.5 py-1 text-[11px] font-medium text-muted-foreground sm:inline-flex"
                title={copilot.knowledge_sources.map((k) => k.name).join(", ")}
              >
                <Database className="size-3" />
                {copilot.knowledge_sources.length} knowledge source
                {copilot.knowledge_sources.length !== 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>

        {/* Messages */}
        <ScrollArea className="flex-1">
          {messages.length === 0 ? (
            <SuggestedPrompts
              copilotName={copilot.name}
              prompts={SUGGESTED_PROMPTS}
              onSelect={(prompt) => handleSend(prompt)}
            />
          ) : (
            <MessageErrorBoundary>
              <MessageList
                messages={messages}
                userInitials={userInitials}
                onRegenerate={handleRegenerate}
              />
            </MessageErrorBoundary>
          )}
        </ScrollArea>

        {/* Input */}
        <div className="border-t border-border bg-card/60 p-3 sm:p-4">
          <ChatInput
            value={input}
            onChange={setInput}
            onSend={() => handleSend()}
            onStop={handleStop}
            isStreaming={isStreaming}
          />
          <p className="mt-2 text-center text-[11px] text-muted-foreground">
            Responses are grounded in your knowledge sources and may still be imperfect. Verify
            anything critical.
          </p>
        </div>
      </div>
    </div>
  );
}
