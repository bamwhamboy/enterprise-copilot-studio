import { ArrowRight, Bell } from "lucide-react";

import { cn } from "@/lib/utils";
import type { MarketplaceCopilotData } from "@/types/dashboard";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function MarketplaceCopilotCard({
  data,
}: {
  data: MarketplaceCopilotData;
}) {
  const isAvailable = data.status === "available";

  return (
    <Card
      className={cn(
        "group relative overflow-hidden transition-shadow hover:shadow-md",
        !isAvailable && "bg-muted/30"
      )}
    >
      <CardContent className="flex h-full flex-col gap-4 pt-6">
        <div className="flex items-start justify-between">
          <div
            className={cn(
              "flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary",
              !isAvailable && "grayscale-[40%] opacity-70"
            )}
          >
            <data.icon className="size-5" />
          </div>
          <Badge variant={isAvailable ? "success" : "secondary"}>
            {isAvailable ? "Available" : "Coming Soon"}
          </Badge>
        </div>

        <div className="flex flex-1 flex-col gap-1">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {data.category}
          </span>
          <span className="text-sm font-semibold text-foreground">
            {data.name}
          </span>
          <p className="text-xs text-muted-foreground">{data.description}</p>
        </div>

        <Button
          variant={isAvailable ? "default" : "outline"}
          size="sm"
          className="w-full"
          disabled={!isAvailable}
        >
          {isAvailable ? (
            <>
              Launch Copilot
              <ArrowRight className="size-3.5" />
            </>
          ) : (
            <>
              Notify Me
              <Bell className="size-3.5" />
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
