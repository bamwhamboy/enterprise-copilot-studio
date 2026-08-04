"use client";

import { ArrowRight, Database, Blocks, Wallet, Timer } from "lucide-react";
import { motion } from "framer-motion";

import { useCreateCopilotStore } from "@/app/create-copilot/store/create-copilot-store";
import { knowledgeSources } from "@/app/create-copilot/components/step-knowledge-sources";
import { aiComponents } from "@/app/create-copilot/components/step-ai-components";
import { modelOptions } from "@/app/create-copilot/components/step-model-selection";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

const architectureChainLabels = [
  "Enterprise Retrieval Engine",
  "Planner Agent",
  "Conversation Memory",
  "LLM Router",
];

export function StepReview() {
  const { basicInfo, knowledgeSourceIds, aiComponentIds, modelId } =
    useCreateCopilotStore();

  const selectedModel =
    modelOptions.find((m) => m.id === modelId) ?? modelOptions[0];

  const selectedSourceLabels = knowledgeSources
    .filter((s) => knowledgeSourceIds.includes(s.id))
    .map((s) => s.label);

  const selectedComponentLabels = aiComponents
    .filter((c) => aiComponentIds.includes(c.id))
    .map((c) => c.label);

  const copilotName = basicInfo.name.trim() || "HR Copilot";
  const chain = [...architectureChainLabels, selectedModel.label];

  return (
    <div className="flex flex-col gap-6">
      <Card className="overflow-hidden bg-gradient-to-br from-primary/5 to-[#5b7cfa]/5">
        <CardContent className="flex flex-col gap-5 pt-6">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Architecture Summary
            </p>
            <h3 className="mt-1 text-lg font-semibold text-foreground">
              {copilotName}
            </h3>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {chain.map((label, index) => (
              <motion.div
                key={label}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.08, duration: 0.3 }}
                className="flex items-center gap-2"
              >
                <span
                  className={
                    index === chain.length - 1
                      ? "rounded-full bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground"
                      : "rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground"
                  }
                >
                  {label}
                </span>
                {index !== chain.length - 1 && (
                  <ArrowRight className="size-3.5 text-muted-foreground" />
                )}
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center gap-2 space-y-0">
            <Database className="size-4 text-muted-foreground" />
            <CardTitle className="text-sm">Knowledge Sources</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-1.5">
            {selectedSourceLabels.length > 0 ? (
              selectedSourceLabels.map((label) => (
                <Badge key={label} variant="outline">
                  {label}
                </Badge>
              ))
            ) : (
              <span className="text-xs text-muted-foreground">
                No knowledge sources selected yet.
              </span>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center gap-2 space-y-0">
            <Blocks className="size-4 text-muted-foreground" />
            <CardTitle className="text-sm">AI Components</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-1.5">
            {selectedComponentLabels.map((label) => (
              <Badge key={label} variant="outline">
                {label}
              </Badge>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center gap-2 space-y-0">
            <Wallet className="size-4 text-muted-foreground" />
            <CardTitle className="text-sm">Estimated Cost</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-xl font-semibold text-foreground">
              {selectedModel.estimatedCost}
            </span>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center gap-2 space-y-0">
            <Timer className="size-4 text-muted-foreground" />
            <CardTitle className="text-sm">Estimated Latency</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-xl font-semibold text-foreground">
              {selectedModel.estimatedLatency}
            </span>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-muted/30">
        <CardHeader>
          <CardTitle className="text-sm">Configuration Summary</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Domain</span>
            <span className="font-medium text-foreground">
              {basicInfo.domain.toUpperCase()}
            </span>
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Model</span>
            <span className="font-medium text-foreground">
              {selectedModel.label} ({selectedModel.provider})
            </span>
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Knowledge Sources</span>
            <span className="font-medium text-foreground">
              {selectedSourceLabels.length} selected
            </span>
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">AI Components</span>
            <span className="font-medium text-foreground">
              {selectedComponentLabels.length} enabled
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
