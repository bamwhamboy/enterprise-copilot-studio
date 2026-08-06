import { Skeleton } from "@/components/ui/skeleton";

/**
 * Shared branded loading state for the login/register pages, shown
 * while the persisted auth store hasn't hydrated yet, or briefly while
 * an already-authenticated visitor is being redirected away -- so
 * neither page ever flashes its form to someone who shouldn't see it.
 */
export function AuthLoadingScreen() {
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
