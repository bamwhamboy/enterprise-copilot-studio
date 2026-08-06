"use client";

import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { MessageSquare } from "lucide-react";

import { copilotsApi } from "@/lib/api/copilots";
import { Button } from "@/components/ui/button";

interface LaunchCopilotButtonProps {
  copilotId: string;
  copilotName: string;
  size?: "default" | "sm" | "lg";
  variant?: "default" | "outline";
  className?: string;
}

/**
 * Launch Copilot navigates straight to the chat interface -- no
 * blocking modal, no "Starting LangGraph..."-style engineering detail
 * shown to the user (that used to be a full-screen animated sequence
 * naming internal implementation technology, which end users should
 * never see; see the chat workspace's own inline loading state for
 * what replaced it). This should feel like clicking into a
 * conversation in ChatGPT/Claude/Copilot, not like watching a
 * deployment pipeline.
 *
 * Still prefetches the copilot's data in the background on hover/click
 * so the chat page typically has it cached and ready by the time it
 * mounts -- a perf optimization, invisible to the user, not a gate on
 * navigation.
 */
export function LaunchCopilotButton({
  copilotId,
  copilotName,
  size = "sm",
  variant = "default",
  className,
}: LaunchCopilotButtonProps) {
  const queryClient = useQueryClient();

  function prefetch() {
    queryClient.prefetchQuery({
      queryKey: ["copilot", copilotId],
      queryFn: () => copilotsApi.get(copilotId),
    });
  }

  return (
    <Button asChild size={size} variant={variant} className={className}>
      <Link
        href={`/copilots/${copilotId}/chat`}
        onMouseEnter={prefetch}
        onFocus={prefetch}
        onClick={prefetch}
        aria-label={`Launch ${copilotName}`}
      >
        Launch Copilot
        <MessageSquare className="size-3.5" />
      </Link>
    </Button>
  );
}
