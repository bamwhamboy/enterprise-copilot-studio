"use client";

import { Check } from "lucide-react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";
import type { WizardStepMeta } from "@/types/create-copilot";

export const WIZARD_STEPS: WizardStepMeta[] = [
  {
    id: "basic-information",
    step: 1,
    title: "Basic Information",
    shortTitle: "Basics",
  },
  {
    id: "knowledge-sources",
    step: 2,
    title: "Knowledge Sources",
    shortTitle: "Knowledge",
  },
  {
    id: "ai-components",
    step: 3,
    title: "AI Components",
    shortTitle: "Components",
  },
  {
    id: "model-selection",
    step: 4,
    title: "Model Selection",
    shortTitle: "Model",
  },
  { id: "review", step: 5, title: "Review Configuration", shortTitle: "Review" },
  { id: "generate", step: 6, title: "Generate Copilot", shortTitle: "Generate" },
];

interface WizardStepperProps {
  currentStep: number;
}

export function WizardStepper({ currentStep }: WizardStepperProps) {
  const progress =
    ((currentStep - 1) / (WIZARD_STEPS.length - 1)) * 100;

  return (
    <div className="w-full">
      {/* Track + fill */}
      <div className="relative mb-3 h-1 w-full overflow-hidden rounded-full bg-border">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-primary to-[#5b7cfa]"
          initial={false}
          animate={{ width: `${progress}%` }}
          transition={{ type: "spring", stiffness: 260, damping: 30 }}
        />
      </div>

      <ol className="grid grid-cols-3 gap-2 sm:grid-cols-6">
        {WIZARD_STEPS.map((step) => {
          const isComplete = step.step < currentStep;
          const isCurrent = step.step === currentStep;

          return (
            <li key={step.id} className="flex flex-col items-center gap-1.5">
              <div
                className={cn(
                  "flex size-7 items-center justify-center rounded-full border text-xs font-semibold transition-colors",
                  isComplete &&
                    "border-primary bg-primary text-primary-foreground",
                  isCurrent &&
                    "border-primary bg-primary/10 text-primary ring-4 ring-primary/10",
                  !isComplete &&
                    !isCurrent &&
                    "border-border bg-muted text-muted-foreground"
                )}
              >
                {isComplete ? <Check className="size-3.5" /> : step.step}
              </div>
              <span
                className={cn(
                  "hidden text-center text-[11px] font-medium leading-tight sm:block",
                  isCurrent ? "text-foreground" : "text-muted-foreground"
                )}
              >
                {step.shortTitle}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
