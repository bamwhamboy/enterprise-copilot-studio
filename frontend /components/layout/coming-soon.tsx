import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

interface ComingSoonProps {
  icon: LucideIcon;
  message?: string;
}

export function ComingSoon({ icon: Icon, message }: ComingSoonProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center gap-3 py-24 text-center">
        <div className="flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary">
          <Icon className="size-6" />
        </div>
        <p className="text-sm font-medium text-foreground">
          {message ?? "This section is under construction."}
        </p>
        <p className="max-w-sm text-xs text-muted-foreground">
          The UI foundation is ready — feature logic will be built on top of
          this layout.
        </p>
      </CardContent>
    </Card>
  );
}
