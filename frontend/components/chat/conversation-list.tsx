"use client";

import { MessageSquarePlus, MessageSquare, Trash2 } from "lucide-react";

import { cn } from "@/lib/utils";
import type { ChatSession } from "@/store/chat-store";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";

interface ConversationListProps {
  sessions: ChatSession[];
  activeSessionId: string | undefined;
  onSelect: (sessionId: string) => void;
  onNew: () => void;
  onDelete: (sessionId: string) => void;
}

export function ConversationList({
  sessions,
  activeSessionId,
  onSelect,
  onNew,
  onDelete,
}: ConversationListProps) {
  return (
    <div className="flex h-full min-h-0 flex-col border-r border-border bg-card/40">
      <div className="p-3">
        <Button variant="outline" className="w-full justify-start gap-2" onClick={onNew}>
          <MessageSquarePlus className="size-4" />
          New conversation
        </Button>
      </div>
      <ScrollArea className="min-h-0 flex-1 px-2">
        <div className="flex flex-col gap-1 pb-3">
          {sessions.length === 0 && (
            <p className="px-2.5 py-6 text-center text-xs text-muted-foreground">
              Your conversations with this copilot will appear here.
            </p>
          )}
          {sessions.map((session) => (
            <div
              key={session.id}
              className={cn(
                "group flex items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors",
                session.id === activeSessionId
                  ? "bg-primary/10 text-primary"
                  : "text-foreground hover:bg-accent"
              )}
            >
              <button
                onClick={() => onSelect(session.id)}
                className="flex min-w-0 flex-1 items-center gap-2"
              >
                <MessageSquare className="size-3.5 shrink-0 opacity-70" />
                <span className="truncate">{session.title}</span>
              </button>
              <button
                onClick={() => onDelete(session.id)}
                className="shrink-0 rounded-md p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                aria-label="Delete conversation"
              >
                <Trash2 className="size-3.5" />
              </button>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
