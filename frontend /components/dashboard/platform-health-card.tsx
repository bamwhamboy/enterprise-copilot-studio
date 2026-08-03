import { cn } from "@/lib/utils";
import type { PlatformHealthData } from "@/types/dashboard";
import { Card, CardContent } from "@/components/ui/card";

const statusConfig = {
  healthy: {
    label: "Operational",
    dot: "bg-success",
    text: "text-success",
    ring: "ring-success/20",
  },
  degraded: {
    label: "Degraded",
    dot: "bg-warning",
    text: "text-warning",
    ring: "ring-warning/20",
  },
  down: {
    label: "Down",
    dot: "bg-destructive",
    text: "text-destructive",
    ring: "ring-destructive/20",
  },
};

export function PlatformHealthCard({ data }: { data: PlatformHealthData }) {
  const status = statusConfig[data.status];

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardContent className="flex items-start gap-3 pt-6">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-foreground/70">
          <data.icon className="size-4" />
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-sm font-medium text-foreground">
              {data.name}
            </span>
            <span
              className={cn(
                "flex size-2.5 shrink-0 rounded-full ring-4",
                status.dot,
                status.ring
              )}
            />
          </div>
          <span className="text-xs text-muted-foreground">
            {data.description}
          </span>
          <div className="mt-1 flex items-center justify-between text-xs">
            <span className={cn("font-medium", status.text)}>
              {status.label}
            </span>
            <span className="text-muted-foreground/70">
              {data.lastUpdated}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
