"use client";

import { Bot, Database, Cpu, Sparkles } from "lucide-react";

import type { ApiKnowledgeSource } from "@/types/knowledge-source";
import { copilotTemplates } from "@/lib/copilot-templates";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const CAPABILITY_LABELS: Record<string, string> = {
  guardrails: "Guardrails",
  authentication: "Authentication",
  citations: "Citations",
  memory: "Conversation Memory",
  "semantic-search": "Semantic Search",
  "pii-protection": "PII Protection",
};

interface StepReviewProps {
  templateId: string | null;
  name: string;
  description: string;
  knowledgeSources: ApiKnowledgeSource[];
  selectedSourceIds: string[];
  model: string;
  capabilities: string[];
}

export function StepReview({
  templateId,
  name,
  description,
  knowledgeSources,
  selectedSourceIds,
  model,
  capabilities,
}: StepReviewProps) {
  const template = copilotTemplates.find((t) => t.id === templateId);
  const selectedSources = knowledgeSources.filter((s) => selectedSourceIds.includes(s.id));

  return (
    <div className="flex flex-col gap-4">
      <Card className="overflow-hidden">
        <CardContent className="flex items-start gap-4 pt-6">
          <div
            className={`flex size-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${template?.accent ?? "from-primary/15 to-[#5b7cfa]/15 text-primary"}`}
          >
            {template ? <template.icon className="size-6" /> : <Bot className="size-6" />}
          </div>
          <div>
            <p className="text-base font-semibold text-foreground">{name || "Untitled Copilot"}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {description || "No description provided."}
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Card>
          <CardContent className="pt-6">
            <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Database className="size-3.5" />
              Knowledge Sources
            </p>
            {selectedSources.length === 0 ? (
              <p className="text-sm text-muted-foreground">None linked</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {selectedSources.map((s) => (
                  <Badge key={s.id} variant="outline">
                    {s.name}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Cpu className="size-3.5" />
              Model
            </p>
            <Badge variant="outline" className="font-mono text-xs">
              {model}
            </Badge>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="pt-6">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
            <Sparkles className="size-3.5" />
            Capabilities
          </p>
          {capabilities.length === 0 ? (
            <p className="text-sm text-muted-foreground">None selected</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {capabilities.map((id) => (
                <Badge key={id} variant="success">
                  {CAPABILITY_LABELS[id] ?? id}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
