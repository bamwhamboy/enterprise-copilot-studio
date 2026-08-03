import type { LucideIcon } from "lucide-react";

export type TrendDirection = "up" | "down" | "flat";

export interface StatCardData {
  id: string;
  label: string;
  value: string;
  icon: LucideIcon;
  trendLabel?: string;
  trendDirection?: TrendDirection;
}

export interface PlaceholderSectionData {
  id: string;
  title: string;
  description?: string;
}
