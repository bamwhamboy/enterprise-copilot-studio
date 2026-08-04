"use client";

import {
  SearchCode,
  Workflow,
  BrainCircuit,
  Wrench,
  ShieldCheck,
  ShieldAlert,
  ScrollText,
  Gauge,
  Router,
  Check,
} from "lucide-react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";
import type { AiComponentOption } from "@/types/create-copilot";
import { useCreateCopilotStore } from "@/app/create-copilot/store/create-copilot-store";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export const aiComponents: AiComponentOption[] = [
  {
    id: "retrieval-engine",
    label: "Enterprise Retrieval Engine",
    description: "Hierarchical hybrid RAG with re-ranking.",
    tooltip:
      "Combines dense + BM25 hybrid search with re-ranking and citation generation.",
    icon: SearchCode,
  },
  {
    id: "planner-agent",
    label: "Planner Agent",
    description: "Breaks requests into orchestrated steps.",
    tooltip:
      "LangGraph-based agent that plans and sequences tool calls to fulfil a request.",
    icon: Workflow,
  },
  {
    id: "conversation-memory",
    label: "Conversation Memory",
    description: "Retains context across turns.",
    tooltip:
      "Short and long-term memory so the copilot remembers earlier parts of the conversation.",
    icon: BrainCircuit,
  },
  {
    id: "tool-calling",
    label: "Tool Calling",
    description: "Invokes external tools and APIs.",
    tooltip: "Lets the copilot call structured tools, functions, or APIs as needed.",
    icon: Wrench,
  },
  {
    id: "prompt-sanitization",
    label: "Prompt Sanitization",
    description: "Filters unsafe or injected input.",
    tooltip:
      "Detects and blocks prompt injection and unsafe input before it reaches the model.",
    icon: ShieldCheck,
  },
  {
    id: "guardrails",
    label: "Guardrails",
    description: "Enforces safe, on-policy responses.",
    tooltip: "Applies output-side policy checks to keep responses safe and on-topic.",
    icon: ShieldAlert,
  },
  {
    id: "context-summarization",
    label: "Context Summarization",
    description: "Condenses long retrieved context.",
    tooltip:
      "Summarizes lengthy retrieved documents to fit more relevant signal into context.",
    icon: ScrollText,
  },
  {
    id: "semantic-cache",
    label: "Semantic Cache",
    description: "Reuses answers to similar queries.",
    tooltip: "Caches responses by semantic similarity to cut cost and latency.",
    icon: Gauge,
  },
  {
    id: "llm-routing",
    label: "LLM Routing",
    description: "Routes requests to the best model.",
    tooltip:
      "Dynamically routes requests across models based on cost, latency, and complexity.",
    icon: Router,
  },
];

export function StepAiComponents() {
  const { aiComponentIds, toggleAiComponent } = useCreateCopilotStore();

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Enable the reusable AI components this copilot should be composed
        from. Recommended components are selected by default.
      </p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {aiComponents.map((component) => {
          const isSelected = aiComponentIds.includes(component.id);

          return (
            <Tooltip key={component.id} delayDuration={200}>
              <TooltipTrigger asChild>
                <motion.button
                  type="button"
                  whileHover={{ y: -2 }}
                  onClick={() => toggleAiComponent(component.id)}
                  className={cn(
                    "relative flex flex-col gap-3 rounded-xl border border-border bg-card p-4 text-left transition-all",
                    "hover:border-primary/40 hover:shadow-md",
                    isSelected &&
                      "border-primary bg-primary/5 ring-2 ring-primary/20"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary">
                      <component.icon className="size-4" />
                    </div>
                    <span
                      className={cn(
                        "flex size-5 items-center justify-center rounded-full border transition-colors",
                        isSelected
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-border bg-transparent"
                      )}
                    >
                      {isSelected && <Check className="size-3" />}
                    </span>
                  </div>

                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-semibold text-foreground">
                      {component.label}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {component.description}
                    </span>
                  </div>
                </motion.button>
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-64">
                {component.tooltip}
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
}
