import { Loader2 } from "lucide-react";

/**
 * Suspense fallback for the chat workspace route, same reasoning as
 * app/knowledge-sources/[id]/loading.tsx -- this route also awaits
 * `params` with no prior loading boundary.
 */
export default function ChatWorkspaceLoading() {
  return (
    <div className="flex h-[calc(100vh-6rem)] items-center justify-center">
      <Loader2 className="size-6 animate-spin text-muted-foreground" />
    </div>
  );
}
