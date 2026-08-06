"use client";

import { memo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";
import {
  Bot,
  Copy,
  Check,
  RotateCcw,
  ThumbsUp,
  ThumbsDown,
  ChevronDown,
  Quote,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/chat";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ConfidenceBadge } from "@/components/chat/confidence-badge";
import { CitationCard } from "@/components/chat/citation-card";
import { StreamingCursor } from "@/components/chat/streaming-cursor";

interface MessageBubbleProps {
  message: ChatMessage;
  userInitials: string;
  isLastAssistantMessage: boolean;
  onRegenerate: () => void;
}

export const MessageBubble = memo(function MessageBubble({
  message,
  userInitials,
  isLastAssistantMessage,
  onRegenerate,
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);
  const [citationsOpen, setCitationsOpen] = useState(false);
  const isUser = message.role === "user";

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API unavailable — silently no-op rather than throw.
    }
  }

  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="flex items-start justify-end gap-3"
      >
        <div className="max-w-[70%] rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground shadow-sm">
          {message.content}
        </div>
        <Avatar className="mt-0.5 size-7 shrink-0">
          <AvatarFallback className="bg-secondary text-[11px] text-secondary-foreground">
            {userInitials}
          </AvatarFallback>
        </Avatar>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="flex items-start gap-3"
    >
      <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-[#5b7cfa] shadow-sm">
        <Bot className="size-3.5 text-primary-foreground" />
      </div>

      <div className="flex max-w-[78%] flex-col gap-2">
        <div className="rounded-2xl rounded-tl-sm border border-border bg-card px-4 py-3 text-sm leading-relaxed text-card-foreground shadow-sm">
          {message.content.length === 0 && message.isStreaming ? (
            <span className="flex items-center gap-1 py-0.5">
              <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
              <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
              <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground" />
            </span>
          ) : message.isStreaming ? (
            // Plain text while streaming: re-parsing the full markdown AST
            // on every single delta chunk is expensive enough (for a
            // longer response) to noticeably jank the main thread, which
            // is what made the whole app feel unresponsive during
            // generation. Switches to full Markdown rendering below once
            // the message settles.
            <p className="whitespace-pre-wrap">
              {message.content}
              <StreamingCursor />
            </p>
          ) : (
            <div className="prose prose-sm max-w-none prose-p:leading-relaxed prose-p:my-1.5 prose-pre:bg-muted prose-pre:text-foreground prose-code:text-foreground prose-headings:mt-2 prose-headings:mb-1.5 prose-ul:my-1.5 prose-ol:my-1.5 dark:prose-invert">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {!message.isStreaming && (
          <>
            {(message.confidence !== undefined || message.citations?.length) && (
              <div className="flex flex-wrap items-center gap-2">
                {message.confidence !== undefined && (
                  <ConfidenceBadge confidence={message.confidence} />
                )}
                {message.citations && message.citations.length > 0 && (
                  <button
                    onClick={() => setCitationsOpen((v) => !v)}
                    className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/60 px-2.5 py-1 text-[11px] font-medium text-muted-foreground transition-colors hover:bg-muted"
                  >
                    <Quote className="size-3" />
                    {message.citations.length} source
                    {message.citations.length !== 1 ? "s" : ""}
                    <ChevronDown
                      className={cn(
                        "size-3 transition-transform",
                        citationsOpen && "rotate-180"
                      )}
                    />
                  </button>
                )}
              </div>
            )}

            {citationsOpen && message.citations && message.citations.length > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="flex flex-col gap-1.5 overflow-hidden"
              >
                {message.citations.map((citation, index) => (
                  <CitationCard key={index} citation={citation} index={index} />
                ))}
              </motion.div>
            )}

            <div className="flex items-center gap-1">
              <button
                onClick={handleCopy}
                className="flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                aria-label="Copy response"
                title="Copy response"
              >
                {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
              </button>
              {isLastAssistantMessage && (
                <button
                  onClick={onRegenerate}
                  className="flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                  aria-label="Regenerate response"
                  title="Regenerate response"
                >
                  <RotateCcw className="size-3.5" />
                </button>
              )}
              <button
                onClick={() => setFeedback(feedback === "up" ? null : "up")}
                className={cn(
                  "flex size-7 items-center justify-center rounded-md transition-colors hover:bg-accent hover:text-accent-foreground",
                  feedback === "up" ? "text-success" : "text-muted-foreground"
                )}
                aria-label="Good response"
                aria-pressed={feedback === "up"}
                title="Good response"
              >
                <ThumbsUp className="size-3.5" />
              </button>
              <button
                onClick={() => setFeedback(feedback === "down" ? null : "down")}
                className={cn(
                  "flex size-7 items-center justify-center rounded-md transition-colors hover:bg-accent hover:text-accent-foreground",
                  feedback === "down" ? "text-destructive" : "text-muted-foreground"
                )}
                aria-label="Poor response"
                aria-pressed={feedback === "down"}
                title="Poor response"
              >
                <ThumbsDown className="size-3.5" />
              </button>
            </div>
          </>
        )}
      </div>
    </motion.div>
  );
});
