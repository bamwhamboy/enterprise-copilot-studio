import { cn } from "@/lib/utils";
import type { ActivityItemData } from "@/types/dashboard";

const statusDot = {
  success: "bg-success",
  info: "bg-primary",
  warning: "bg-warning",
};

export function ActivityTimeline({ items }: { items: ActivityItemData[] }) {
  return (
    <ol className="flex flex-col">
      {items.map((item, index) => (
        <li key={item.id} className="relative flex gap-3 pb-6 last:pb-0">
          {index !== items.length - 1 && (
            <span className="absolute left-[15px] top-8 h-[calc(100%-1.25rem)] w-px bg-border" />
          )}
          <div className="relative flex size-8 shrink-0 items-center justify-center rounded-full border border-border bg-card">
            <item.icon className="size-3.5 text-foreground/70" />
            <span
              className={cn(
                "absolute -right-0.5 -top-0.5 size-2 rounded-full ring-2 ring-card",
                statusDot[item.status]
              )}
            />
          </div>
          <div className="flex flex-1 flex-col gap-0.5 pt-0.5">
            <div className="flex flex-wrap items-baseline justify-between gap-x-2">
              <span className="text-sm font-medium text-foreground">
                {item.title}
              </span>
              <span className="text-xs text-muted-foreground/70">
                {item.timestamp}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {item.description}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}
