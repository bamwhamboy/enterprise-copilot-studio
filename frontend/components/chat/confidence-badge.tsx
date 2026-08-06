import { cn } from "@/lib/utils";

interface ConfidenceBadgeProps {
  confidence: number; // 0-1
  className?: string;
}

function tierFor(confidence: number) {
  if (confidence >= 0.66) return { label: "High confidence", color: "bg-success/10 text-success" };
  if (confidence >= 0.33)
    return { label: "Moderate confidence", color: "bg-warning/10 text-warning" };
  return { label: "Low confidence", color: "bg-destructive/10 text-destructive" };
}

export function ConfidenceBadge({ confidence, className }: ConfidenceBadgeProps) {
  const tier = tierFor(confidence);
  const percent = Math.round(confidence * 100);

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium",
        tier.color,
        className
      )}
      title={tier.label}
    >
      <span className="relative flex size-1.5">
        <span className="absolute inline-flex size-full rounded-full bg-current opacity-60" />
      </span>
      {tier.label} · {percent}%
    </span>
  );
}
