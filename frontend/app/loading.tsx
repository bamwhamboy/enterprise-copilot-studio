import { Skeleton } from "@/components/ui/skeleton";

/**
 * Root-level Suspense fallback -- Next.js shows this instantly for any
 * route transition where the target route needs a moment to resolve,
 * app-wide. Defense-in-depth alongside the per-route loading.tsx files
 * (app/knowledge-sources/[id]/loading.tsx, app/copilots/[copilotId]/
 * chat/loading.tsx) against ever showing a blank screen during
 * navigation, including the login/logout transition.
 */
export default function RootLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4">
        <div className="flex size-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-[#5b7cfa] shadow-lg shadow-primary/25">
          <span className="text-lg font-bold text-primary-foreground">E</span>
        </div>
        <Skeleton className="h-2 w-32 rounded-full" />
      </div>
    </div>
  );
}
