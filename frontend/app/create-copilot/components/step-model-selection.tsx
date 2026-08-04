"use client";

import { Rocket, Sparkles, MessageCircle, Gem, Brain, Lock } from "lucide-react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";
import type { ModelOption } from "@/types/create-copilot";
import { useCreateCopilotStore } from "@/app/create-copilot/store/create-copilot-store";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

export const modelOptions: ModelOption[] = [
  {
    id: "groq-llama-3",
    label: "Groq Llama 3",
    provider: "Groq",
    available: true,
    recommended: true,
    tags: ["Fast", "Low Cost"],
    estimatedCost: "$0.05 / 1K tokens",
    estimatedLatency: "~180ms",
    contextWindow: "8K tokens",
  },
  {
    id: "gpt-5",
    label: "GPT-5",
    provider: "OpenAI",
    available: false,
    estimatedCost: "$2.50 / 1K tokens",
    estimatedLatency: "~900ms",
    contextWindow: "128K tokens",
  },
  {
    id: "claude",
    label: "Claude",
    provider: "Anthropic",
    available: false,
    estimatedCost: "$3.00 / 1K tokens",
    estimatedLatency: "~850ms",
    contextWindow: "200K tokens",
  },
  {
    id: "gemini",
    label: "Gemini",
    provider: "Google",
    available: false,
    estimatedCost: "$1.75 / 1K tokens",
    estimatedLatency: "~750ms",
    contextWindow: "1M tokens",
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    provider: "DeepSeek",
    available: false,
    estimatedCost: "$0.55 / 1K tokens",
    estimatedLatency: "~600ms",
    contextWindow: "64K tokens",
  },
];

const modelIcons: Record<string, typeof Rocket> = {
  "groq-llama-3": Rocket,
  "gpt-5": Sparkles,
  claude: MessageCircle,
  gemini: Gem,
  deepseek: Brain,
};

export function StepModelSelection() {
  const { modelId, setModel } = useCreateCopilotStore();

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Choose the model that powers this copilot. Additional providers can
        be enabled once your platform admin approves them.
      </p>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {modelOptions.map((model) => {
          const Icon = modelIcons[model.id] ?? Sparkles;
          const isSelected = model.id === modelId;

          return (
            <motion.button
              key={model.id}
              type="button"
              disabled={!model.available}
              whileHover={model.available ? { y: -2 } : undefined}
              onClick={() => model.available && setModel(model.id)}
              className={cn(
                "relative flex flex-col gap-4 rounded-xl border border-border bg-card p-4 text-left transition-all",
                model.available &&
                  "cursor-pointer hover:border-primary/40 hover:shadow-md",
                isSelected &&
                  "border-primary bg-primary/5 ring-2 ring-primary/20",
                !model.available && "cursor-not-allowed opacity-50"
              )}
            >
              {!model.available && (
                <Lock className="absolute right-4 top-4 size-3.5 text-muted-foreground" />
              )}

              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      "flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary",
                      !model.available && "grayscale"
                    )}
                  >
                    <Icon className="size-5" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-foreground">
                      {model.label}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {model.provider}
                    </p>
                  </div>
                </div>
                {model.recommended && (
                  <Badge variant="default">Recommended</Badge>
                )}
                {!model.available && (
                  <Badge variant="secondary">Coming Soon</Badge>
                )}
              </div>

              {model.tags && (
                <div className="flex flex-wrap gap-1.5">
                  {model.tags.map((tag) => (
                    <Badge key={tag} variant="outline">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}

              <Separator />

              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="flex flex-col gap-0.5">
                  <span className="text-xs text-muted-foreground">Cost</span>
                  <span className="text-xs font-medium text-foreground">
                    {model.estimatedCost}
                  </span>
                </div>
                <div className="flex flex-col gap-0.5 border-x border-border">
                  <span className="text-xs text-muted-foreground">
                    Latency
                  </span>
                  <span className="text-xs font-medium text-foreground">
                    {model.estimatedLatency}
                  </span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-xs text-muted-foreground">
                    Context
                  </span>
                  <span className="text-xs font-medium text-foreground">
                    {model.contextWindow}
                  </span>
                </div>
              </div>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
