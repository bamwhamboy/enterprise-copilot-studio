import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

import { cn } from "@/lib/utils";
import type { StatCardData } from "@/types/dashboard";
import { Card, CardContent } from "@/components/ui/card";
import { AnimatedCounter } from "@/components/dashboard/animated-counter";

const trendConfig = {
  up: { icon: ArrowUpRight, className: "text-success" },
  down: { icon: ArrowDownRight, className: "text-destructive" },
  flat: { icon: Minus, className: "text-muted-foreground" },
};

export function StatCard({ data }: { data: StatCardData }) {
  const { label, value, icon: Icon, trendLabel, trendDirection } = data;
  const trend = trendDirection ? trendConfig[trendDirection] : null;
  const TrendIcon = trend?.icon;

  return (
    <Card className="relative overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-primary/5">
      <div className="pointer-events-none absolute -right-6 -top-6 size-24 rounded-full bg-gradient-to-br from-primary/10 to-transparent blur-2xl" />
      <CardContent className="flex items-start justify-between gap-4 pt-6">
        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-muted-foreground">
            {label}
          </span>
          <span className="text-2xl font-semibold tracking-tight text-foreground tabular-nums">
            <AnimatedCounter value={value} />
          </span>
          {trendLabel && TrendIcon && (
            <span
              className={cn(
                "flex items-center gap-1 text-xs font-medium",
                trend?.className
              )}
            >
              <TrendIcon className="size-3.5" />
              {trendLabel}
            </span>
          )}
        </div>
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary">
          <Icon className="size-5" />
        </div>
      </CardContent>
    </Card>
  );
}
