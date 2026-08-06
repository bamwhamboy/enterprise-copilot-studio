import { Skeleton } from "@/components/ui/skeleton";

/**
 * Next.js Suspense fallback for this dynamic route. Without this file,
 * a route with an async Server Component (this one awaits `params`) has
 * no instant fallback UI during navigation/refresh -- the browser can
 * show a blank screen until the server finishes resolving the page.
 * This guarantees something renders immediately instead.
 */
export default function KnowledgeSourceDetailLoading() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <Skeleton className="size-10 rounded-xl" />
        <div className="flex flex-col gap-2">
          <Skeleton className="h-5 w-48 rounded-md" />
          <Skeleton className="h-3 w-32 rounded-md" />
        </div>
      </div>
      <Skeleton className="h-40 w-full rounded-xl" />
      <Skeleton className="h-64 w-full rounded-xl" />
    </div>
  );
}
