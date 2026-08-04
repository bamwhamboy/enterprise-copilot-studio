import type { LucideIcon } from "lucide-react";

export type WizardStepId =
  | "basic-information"
  | "knowledge-sources"
  | "ai-components"
  | "model-selection"
  | "review"
  | "generate";

export interface WizardStepMeta {
  id: WizardStepId;
  step: number;
  title: string;
  shortTitle: string;
}

export interface DomainOption {
  id: string;
  label: string;
  icon: LucideIcon;
  available: boolean;
}

export type SourceStatus = "available" | "coming-soon";

export interface KnowledgeSourceOption {
  id: string;
  label: string;
  description: string;
  icon: LucideIcon;
  status: SourceStatus;
}

export interface AiComponentOption {
  id: string;
  label: string;
  description: string;
  tooltip: string;
  icon: LucideIcon;
}

export interface ModelOption {
  id: string;
  label: string;
  provider: string;
  available: boolean;
  recommended?: boolean;
  tags?: string[];
  estimatedCost: string;
  estimatedLatency: string;
  contextWindow: string;
}

export interface GenerationStepItem {
  id: string;
  label: string;
}
