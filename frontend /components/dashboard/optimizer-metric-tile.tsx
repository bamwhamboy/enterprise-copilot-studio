import type { OptimizerMetricData } from "@/types/dashboard";

export function OptimizerMetricTile({ data }: { data: OptimizerMetricData }) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary">
            <data.icon className="size-4" />
          </div>
          <span className="text-sm font-medium text-foreground">
            {data.label}
          </span>
        </div>
        <span className="text-sm font-semibold text-foreground">
          {data.value}
        </span>
      </div>

      {typeof data.progress === "number" && (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary to-[#5b7cfa]"
            style={{ width: `${data.progress}%` }}
          />
        </div>
      )}

      <p className="text-xs text-muted-foreground">{data.description}</p>
    </div>
  );
}
