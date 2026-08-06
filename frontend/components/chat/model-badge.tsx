import { Cpu } from "lucide-react";

export function ModelBadge({ model }: { model: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/60 px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
      <Cpu className="size-3" />
      {model}
    </span>
  );
}
