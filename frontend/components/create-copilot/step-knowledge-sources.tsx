"use client";

import {
  FileText,
  Database,
  Share2,
  BookOpen,
  Webhook,
  Cloud,
  Snowflake,
  Server,
  Check,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { ApiKnowledgeSource } from "@/types/knowledge-source";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";

const CONNECTOR_TYPES = [
  { id: "pdf", label: "PDF", icon: FileText, enabled: true },
  { id: "database", label: "Database", icon: Database, enabled: false },
  { id: "sharepoint", label: "SharePoint", icon: Share2, enabled: false },
  { id: "confluence", label: "Confluence", icon: BookOpen, enabled: false },
  { id: "rest-api", label: "REST API", icon: Webhook, enabled: false },
  { id: "s3", label: "Amazon S3", icon: Cloud, enabled: false },
  { id: "azure-blob", label: "Azure Blob Storage", icon: Server, enabled: false },
  { id: "snowflake", label: "Snowflake", icon: Snowflake, enabled: false },
];

interface StepKnowledgeSourcesProps {
  knowledgeSources: ApiKnowledgeSource[];
  selectedIds: string[];
  onToggle: (id: string) => void;
}

export function StepKnowledgeSources({
  knowledgeSources,
  selectedIds,
  onToggle,
}: StepKnowledgeSourcesProps) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="mb-3 text-sm font-medium text-foreground">Your knowledge sources</p>
        {knowledgeSources.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border px-4 py-6 text-center text-xs text-muted-foreground">
            No knowledge sources yet. You can create one from the Knowledge Sources page and
            link it to this copilot later.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {knowledgeSources.map((source) => {
              const isSelected = selectedIds.includes(source.id);
              return (
                <label
                  key={source.id}
                  className={cn(
                    "flex cursor-pointer items-center gap-3 rounded-lg border px-3.5 py-2.5 transition-colors",
                    isSelected ? "border-primary/40 bg-primary/5" : "border-border hover:bg-accent/40"
                  )}
                >
                  <Checkbox checked={isSelected} onCheckedChange={() => onToggle(source.id)} />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">{source.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {source.documents.length} document{source.documents.length !== 1 ? "s" : ""}
                    </p>
                  </div>
                </label>
              );
            })}
          </div>
        )}
      </div>

      <div>
        <p className="mb-3 text-sm font-medium text-foreground">Enterprise connectors</p>
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          {CONNECTOR_TYPES.map((connector) => (
            <div
              key={connector.id}
              className={cn(
                "flex flex-col items-center gap-2 rounded-xl border px-3 py-4 text-center",
                connector.enabled
                  ? "border-primary/30 bg-primary/5"
                  : "border-border bg-muted/30 opacity-60 grayscale-[30%]"
              )}
            >
              <connector.icon className="size-5 text-foreground/70" />
              <span className="text-xs font-medium text-foreground">{connector.label}</span>
              {connector.enabled ? (
                <Badge variant="success" className="gap-1 text-[10px]">
                  <Check className="size-2.5" />
                  Ready
                </Badge>
              ) : (
                <Badge variant="secondary" className="text-[10px]">
                  Coming Soon
                </Badge>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
