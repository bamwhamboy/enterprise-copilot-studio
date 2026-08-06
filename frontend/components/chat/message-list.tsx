"use client";

import { useEffect, useRef } from "react";

import type { ChatMessage } from "@/types/chat";
import { MessageBubble } from "@/components/chat/message-bubble";
import { MessageErrorBoundary } from "@/components/chat/message-error-boundary";
import { Skeleton } from "@/components/ui/skeleton";

interface MessageListProps {
  messages: ChatMessage[];
  userInitials: string;
  onRegenerate: () => void;
}

export function MessageList({ messages, userInitials, onRegenerate }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const lastMessageContent = messages[messages.length - 1]?.content;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, lastMessageContent]);

  const lastAssistantIndex = [...messages]
    .map((m, i) => ({ m, i }))
    .reverse()
    .find(({ m }) => m.role === "assistant")?.i;

  return (
    <div className="flex flex-col gap-5 px-4 py-6 sm:px-8">
      {messages.map((message, index) => (
        <MessageErrorBoundary key={message.id}>
          <MessageBubble
            message={message}
            userInitials={userInitials}
            isLastAssistantMessage={index === lastAssistantIndex && !message.isStreaming}
            onRegenerate={onRegenerate}
          />
        </MessageErrorBoundary>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

export function MessageListSkeleton() {
  return (
    <div className="flex flex-col gap-6 px-4 py-6 sm:px-8">
      {[0, 1].map((i) => (
        <div key={i} className="flex items-start gap-3">
          <Skeleton className="size-7 shrink-0 rounded-full" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-4 w-2/3 rounded-md" />
            <Skeleton className="h-4 w-1/2 rounded-md" />
          </div>
        </div>
      ))}
    </div>
  );
}
