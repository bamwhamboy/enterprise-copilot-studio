"use client";

import { useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Circle, Loader2, Rocket, LayoutDashboard } from "lucide-react";

import type { GenerationStepItem } from "@/types/create-copilot";
import { useCreateCopilotStore } from "@/app/create-copilot/store/create-copilot-store";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const generationSteps: GenerationStepItem[] = [
  { id: "validate", label: "Validating Configuration" },
  { id: "create", label: "Creating Copilot" },
  { id: "retrieval", label: "Configuring Enterprise Retrieval Engine" },
  { id: "planner", label: "Initializing Planner Agent" },
  { id: "memory", label: "Enabling Conversation Memory" },
  { id: "guardrails", label: "Applying Guardrails" },
  { id: "llm", label: "Configuring LLM" },
  { id: "deploy", label: "Finalizing Deployment" },
];

const STEP_INTERVAL_MS = 650;

export function StepSuccess() {
  const {
    basicInfo,
    generationStepIndex,
    isGenerationComplete,
    resetGeneration,
    advanceGeneration,
    completeGeneration,
    resetWizard,
  } = useCreateCopilotStore();

  useEffect(() => {
    resetGeneration();

    const timer = setInterval(() => {
      const state = useCreateCopilotStore.getState();
      const isLastStep = state.generationStepIndex + 1 >= generationSteps.length;

      advanceGeneration();

      if (isLastStep) {
        clearInterval(timer);
        completeGeneration();
      }
    }, STEP_INTERVAL_MS);

    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const copilotName = basicInfo.name.trim() || "HR Copilot";

  return (
    <div className="flex flex-col items-center gap-6 py-4">
      <AnimatePresence mode="wait">
        {!isGenerationComplete ? (
          <motion.div
            key="generating"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="w-full max-w-lg"
          >
            <Card className="overflow-hidden">
              <CardContent className="flex flex-col gap-1 pt-6">
                <div className="mb-3 flex flex-col items-center gap-2 text-center">
                  <div className="flex size-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary">
                    <Loader2 className="size-6 animate-spin" />
                  </div>
                  <p className="text-sm font-semibold text-foreground">
                    Generating {copilotName}...
                  </p>
                </div>

                <ul className="flex flex-col">
                  {generationSteps.map((step, index) => {
                    const isDone = index < generationStepIndex;
                    const isCurrent = index === generationStepIndex;

                    return (
                      <motion.li
                        key={step.id}
                        initial={{ opacity: 0.35 }}
                        animate={{
                          opacity: isDone || isCurrent ? 1 : 0.35,
                        }}
                        transition={{ duration: 0.25 }}
                        className="flex items-center gap-3 py-2"
                      >
                        {isDone ? (
                          <CheckCircle2 className="size-4 shrink-0 text-success" />
                        ) : isCurrent ? (
                          <Loader2 className="size-4 shrink-0 animate-spin text-primary" />
                        ) : (
                          <Circle className="size-4 shrink-0 text-muted-foreground/40" />
                        )}
                        <span
                          className={
                            isDone || isCurrent
                              ? "text-sm font-medium text-foreground"
                              : "text-sm text-muted-foreground"
                          }
                        >
                          {step.label}
                        </span>
                      </motion.li>
                    );
                  })}
                </ul>
              </CardContent>
            </Card>
          </motion.div>
        ) : (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="w-full max-w-lg"
          >
            <Card className="overflow-hidden bg-gradient-to-br from-primary/5 to-[#5b7cfa]/5">
              <CardContent className="flex flex-col items-center gap-4 pt-10 pb-8 text-center">
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 260, damping: 14, delay: 0.1 }}
                  className="text-5xl"
                >
                  🎉
                </motion.span>
                <div>
                  <h3 className="text-xl font-semibold text-foreground">
                    {copilotName} Created Successfully
                  </h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Your copilot has been composed and is ready to preview in
                    the marketplace.
                  </p>
                </div>

                <div className="mt-2 flex w-full flex-col gap-2 sm:flex-row sm:justify-center">
                  <Button asChild size="lg" onClick={resetWizard}>
                    <Link href="/marketplace">
                      <Rocket className="size-4" />
                      Launch Copilot
                    </Link>
                  </Button>
                  <Button asChild variant="outline" size="lg" onClick={resetWizard}>
                    <Link href="/">
                      <LayoutDashboard className="size-4" />
                      Return to Dashboard
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
