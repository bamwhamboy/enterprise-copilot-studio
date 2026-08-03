import type { LucideIcon } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface PlaceholderSectionProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  className?: string;
}

export function PlaceholderSection({
  title,
  description,
  icon: Icon,
  className,
}: PlaceholderSectionProps) {
  return (
    <Card className={className}>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="text-base">{title}</CardTitle>
        {Icon && <Icon className="size-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        <div className="flex h-40 flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-muted/30 text-center">
          <span className="text-sm font-medium text-muted-foreground">
            No data yet
          </span>
          {description && (
            <span className="max-w-[24ch] text-xs text-muted-foreground/70">
              {description}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
