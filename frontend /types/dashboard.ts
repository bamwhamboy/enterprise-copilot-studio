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

export type HealthStatus = "healthy" | "degraded" | "down";

export interface PlatformHealthData {
  id: string;
  name: string;
  description: string;
  status: HealthStatus;
  icon: LucideIcon;
  lastUpdated: string;
}

export type MarketplaceCopilotStatus = "available" | "coming-soon";

export interface MarketplaceCopilotData {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
  status: MarketplaceCopilotStatus;
  category: string;
}

export interface OptimizerMetricData {
  id: string;
  label: string;
  value: string;
  progress?: number;
  icon: LucideIcon;
  description: string;
}

export interface ActivityItemData {
  id: string;
  title: string;
  description: string;
  timestamp: string;
  icon: LucideIcon;
  status: "success" | "info" | "warning";
}

export interface QuickAction {
  id: string;
  label: string;
  icon: LucideIcon;
}
