"use client";

import Link from "next/link";
import { AlertCircle, RotateCw } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  /** Shown alongside Retry when a full escape hatch is useful (e.g. a detail page for a resource that failed to load). Defaults to linking back to the Dashboard. */
  showReturnToDashboard?: boolean;
}

/**
 * Friendly fallback for a failed data request -- shown instead of a
 * spinner that never resolves, or worse, an empty state that looks
 * like "you have nothing" when the real story is "the request failed".
 */
export function ErrorState({
  title = "Unable to complete your request.",
  description = "Something went wrong loading this page. Please try again.",
  onRetry,
  showReturnToDashboard = true,
}: ErrorStateProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
        <div className="flex size-12 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
          <AlertCircle className="size-5" />
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">{title}</p>
          <p className="mt-1 max-w-sm text-xs text-muted-foreground">{description}</p>
        </div>
        <div className="mt-1 flex items-center gap-2">
          {onRetry && (
            <Button size="sm" onClick={onRetry}>
              <RotateCw className="size-3.5" />
              Retry
            </Button>
          )}
          {showReturnToDashboard && (
            <Button asChild size="sm" variant="outline">
              <Link href="/">Return to Dashboard</Link>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
