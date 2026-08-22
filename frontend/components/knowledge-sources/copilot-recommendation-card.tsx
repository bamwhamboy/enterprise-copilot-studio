"use client";

import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Sparkles, X } from "lucide-react";

import type { DocumentClassificationResponse } from "@/types/document-classification";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

const DOMAIN_TEMPLATE_IDS: Record<string, string> = {
  HR: "hr-assistant",
  Finance: "finance-analyst",
  Legal: "legal-advisor",
  "IT Support": "it-support",
};

function confidenceLabel(confidence: number): {
  label: "High" | "Medium" | "Low";
  variant: "success" | "warning" | "secondary";
} {
  if (confidence >= 0.75) return { label: "High", variant: "success" };
  if (confidence >= 0.5) return { label: "Medium", variant: "warning" };
  return { label: "Low", variant: "secondary" };
}

export interface CopilotRecommendationCardProps {
  documentName: string;
  result: DocumentClassificationResponse;
  onDismiss: () => void;
}

export function CopilotRecommendationCard({
  documentName,
  result,
  onDismiss,
}: CopilotRecommendationCardProps) {
  const router = useRouter();
  const { label, variant } = confidenceLabel(result.confidence);
  const templateId = DOMAIN_TEMPLATE_IDS[result.domain];

  function handleCreateCopilot() {
    router.push(templateId ? `/create-copilot?template=${templateId}` : "/create-copilot");
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
    >
      <Card className="border-primary/30 bg-gradient-to-br from-primary/5 to-[#5b7cfa]/5">
        <CardContent className="flex flex-col gap-3 pt-6">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-[#5b7cfa] text-primary-foreground">
                <Sparkles className="size-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">Smart Copilot Recommendation</p>
                <p className="text-xs text-muted-foreground">Based on {documentName}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="size-7 shrink-0 text-muted-foreground"
              onClick={onDismiss}
              aria-label="Dismiss recommendation"
            >
              <X className="size-3.5" />
            </Button>
          </div>

          <div className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-lg border border-border/60 bg-background/60 px-4 py-3 text-sm sm:grid-cols-4">
            <div>
              <p className="text-[11px] text-muted-foreground">Recommended</p>
              <p className="font-medium text-foreground">{result.recommended_copilot}</p>
            </div>
            <div>
              <p className="text-[11px] text-muted-foreground">Document type</p>
              <p className="font-medium text-foreground">{result.document_type}</p>
            </div>
            <div>
              <p className="text-[11px] text-muted-foreground">Confidence</p>
              <Badge variant={variant} className="mt-0.5">
                {label} · {Math.round(result.confidence * 100)}%
              </Badge>
            </div>
            <div>
              <p className="text-[11px] text-muted-foreground">Domain</p>
              <p className="font-medium text-foreground">{result.domain}</p>
            </div>
          </div>

          {result.matched_signals.length > 0 && (
            <div>
              <p className="mb-1 text-[11px] text-muted-foreground">Matched signals</p>
              <div className="flex flex-wrap gap-1.5">
                {result.matched_signals.map((signal) => (
                  <Badge key={signal} variant="outline" className="text-xs">
                    {signal}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-col gap-2 pt-1 sm:flex-row">
            {templateId && (
              <Button onClick={handleCreateCopilot} className="flex-1">
                Create {result.recommended_copilot}
              </Button>
            )}
            <Button variant="ghost" onClick={onDismiss} className="flex-1">
              Continue without creating a Copilot
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
