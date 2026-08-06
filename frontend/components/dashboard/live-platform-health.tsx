"use client";

import { useQuery } from "@tanstack/react-query";
import { Server, Clock } from "lucide-react";

import { checkHealth } from "@/lib/api/health";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";

/**
 * The backend exposes exactly one real health signal (GET /health, a
 * deliberate pure liveness check -- see app/api/v1/health.py's own
 * docstring: it has no DB/Qdrant/Redis dependency so it stays meaningful
 * during a downstream outage). Rather than fabricate a per-service
 * breakdown the backend doesn't provide, this shows that one real
 * signal honestly: live-polled, with real latency and a real timestamp.
 */
export function LivePlatformHealth() {
  const { data, isLoading } = useQuery({
    queryKey: ["platform-health"],
    queryFn: checkHealth,
    refetchInterval: 30_000,
  });

  const isHealthy = data?.ok ?? false;

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardContent className="flex items-start gap-3 pt-6">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-foreground/70">
          <Server className="size-4" />
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-sm font-medium text-foreground">
              Backend API
            </span>
            <span
              className={cn(
                "flex size-2.5 shrink-0 rounded-full ring-4",
                isLoading
                  ? "bg-muted-foreground ring-muted"
                  : isHealthy
                    ? "bg-success ring-success/20"
                    : "bg-destructive ring-destructive/20"
              )}
            />
          </div>
          <span className="text-xs text-muted-foreground">
            {data?.data
              ? `${data.data.app_name} v${data.data.version} · ${data.data.environment}`
              : "GET /health"}
          </span>
          <div className="mt-1 flex items-center justify-between text-xs">
            <span
              className={cn(
                "font-medium",
                isLoading
                  ? "text-muted-foreground"
                  : isHealthy
                    ? "text-success"
                    : "text-destructive"
              )}
            >
              {isLoading ? "Checking…" : isHealthy ? "Operational" : "Unreachable"}
            </span>
            {data && (
              <span className="flex items-center gap-1 text-muted-foreground/70">
                <Clock className="size-3" />
                {data.latencyMs}ms
              </span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
