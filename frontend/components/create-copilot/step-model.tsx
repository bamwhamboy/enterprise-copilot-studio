"use client";

import { Check, Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

const MODELS = [
  {
    id: "openai/gpt-oss-120b",
    label: "GPT-OSS 120B",
    description: "Served via Groq — fast inference with strong reasoning and tool use.",
    enabled: true,
  },
  { id: "gpt-4", label: "GPT-4", description: "OpenAI", enabled: false },
  { id: "claude", label: "Claude", description: "Anthropic", enabled: false },
  { id: "gemini", label: "Gemini", description: "Google", enabled: false },
  { id: "mistral", label: "Mistral", description: "Mistral AI", enabled: false },
];

export function StepModel({ selectedModel }: { selectedModel: string }) {
  return (
    <div className="flex flex-col gap-2.5">
      {MODELS.map((model) => {
        const isSelected = model.enabled && model.id === selectedModel;
        return (
          <div
            key={model.id}
            className={cn(
              "flex items-center gap-3 rounded-xl border px-4 py-3.5",
              isSelected
                ? "border-primary/40 bg-primary/5 ring-1 ring-primary/20"
                : model.enabled
                  ? "border-border"
                  : "border-border bg-muted/30 opacity-60"
            )}
          >
            <div
              className={cn(
                "flex size-9 items-center justify-center rounded-lg",
                model.enabled ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
              )}
            >
              <Sparkles className="size-4" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-foreground">{model.label}</p>
              <p className="text-xs text-muted-foreground">{model.description}</p>
            </div>
            {model.enabled ? (
              <Badge variant="success" className="gap-1">
                <Check className="size-3" />
                Selected
              </Badge>
            ) : (
              <Badge variant="secondary">Coming Soon</Badge>
            )}
          </div>
        );
      })}
    </div>
  );
}
