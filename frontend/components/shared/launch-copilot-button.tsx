"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { MessageSquare, Rocket } from "lucide-react";

import { copilotsApi } from "@/lib/api/copilots";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { SequenceLoader, type SequenceStepDef } from "@/components/shared/sequence-loader";

const LAUNCH_STEPS: SequenceStepDef[] = [
  { id: "connect", label: "Connecting AI…" },
  { id: "knowledge", label: "Loading Knowledge…" },
  { id: "retrieval", label: "Initializing Retrieval…" },
  { id: "langgraph", label: "Starting LangGraph…" },
  { id: "ready", label: "Ready" },
];

// If the real prefetch is still pending once the visual sequence
// finishes, don't wait indefinitely -- navigate anyway (the chat
// workspace has its own loading state for that rare, slow case) rather
// than leave the user stuck on the modal.
const MAX_EXTRA_WAIT_MS = 4000;

interface LaunchCopilotButtonProps {
  copilotId: string;
  copilotName: string;
  size?: "default" | "sm" | "lg";
  variant?: "default" | "outline";
  className?: string;
}

/**
 * A branded loading sequence between clicking "Launch Copilot" and
 * landing in the chat workspace. Genuinely tied to backend readiness,
 * not purely decorative: it prefetches the copilot's data in parallel
 * with the animation, so by the time the animation's visual pace
 * finishes, the chat workspace typically opens with data already
 * cached (instant, no second spinner) -- and if the backend responds
 * before the animation would naturally finish, it doesn't force an
 * artificial extra wait beyond what's needed to feel like a deliberate
 * transition rather than a jarring instant cut.
 */
export function LaunchCopilotButton({
  copilotId,
  copilotName,
  size = "sm",
  variant = "default",
  className,
}: LaunchCopilotButtonProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isLaunching, setIsLaunching] = useState(false);
  const prefetchRef = useRef<Promise<unknown> | null>(null);

  function handleLaunch() {
    setIsLaunching(true);
    // Fire the real prefetch immediately so it runs in parallel with
    // the animation, not after it.
    prefetchRef.current = queryClient.prefetchQuery({
      queryKey: ["copilot", copilotId],
      queryFn: () => copilotsApi.get(copilotId),
    });
  }

  async function handleAnimationComplete() {
    const timeout = new Promise((resolve) => setTimeout(resolve, MAX_EXTRA_WAIT_MS));
    // Whichever finishes first: the real data arriving, or the ceiling
    // -- never block the user on the modal longer than that.
    await Promise.race([prefetchRef.current ?? Promise.resolve(), timeout]);
    router.push(`/copilots/${copilotId}/chat`);
  }

  if (isLaunching) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-[2px]">
        <Card className="w-full max-w-sm">
          <CardContent>
            <SequenceLoader
              title={`Launching ${copilotName}`}
              icon={Rocket}
              steps={LAUNCH_STEPS}
              stepDurationMs={350}
              onComplete={handleAnimationComplete}
            />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <Button size={size} variant={variant} className={className} onClick={handleLaunch}>
      Launch Copilot
      <MessageSquare className="size-3.5" />
    </Button>
  );
}
