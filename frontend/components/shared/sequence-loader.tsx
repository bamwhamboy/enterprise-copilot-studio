"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Loader2, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export interface SequenceStepDef {
  id: string;
  label: string;
}

interface SequenceLoaderProps {
  title: string;
  icon: LucideIcon;
  steps: SequenceStepDef[];
  /** Called once, after the last step completes and a brief settle pause. */
  onComplete: () => void;
  /** Per-step duration; total runtime is roughly steps.length * this. */
  stepDurationMs?: number;
}

/**
 * A reusable animated checklist sequence -- used both for the Create
 * Copilot wizard's completion animation and the Launch Copilot loading
 * screen, so the "steps check off one by one" behavior lives in exactly
 * one place rather than being duplicated between the two flows.
 */
export function SequenceLoader({
  title,
  icon: Icon,
  steps,
  onComplete,
  stepDurationMs = 500,
}: SequenceLoaderProps) {
  const [completedCount, setCompletedCount] = useState(0);

  useEffect(() => {
    if (completedCount >= steps.length) {
      const finishTimer = setTimeout(onComplete, 400);
      return () => clearTimeout(finishTimer);
    }
    const timer = setTimeout(() => setCompletedCount((c) => c + 1), stepDurationMs);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [completedCount, steps.length, stepDurationMs]);

  return (
    <div className="flex flex-col items-center gap-6 py-10 text-center">
      <motion.div
        animate={{ scale: [1, 1.06, 1] }}
        transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
        className="flex size-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-[#5b7cfa] shadow-lg shadow-primary/25"
      >
        <Icon className="size-7 text-primary-foreground" />
      </motion.div>

      <div>
        <p className="text-base font-semibold text-foreground">{title}</p>
      </div>

      <div className="flex w-full max-w-xs flex-col gap-2.5">
        {steps.map((step, index) => {
          const isDone = index < completedCount;
          const isActive = index === completedCount;
          return (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: isDone || isActive ? 1 : 0.35, x: 0 }}
              className="flex items-center gap-2.5 text-left"
            >
              <span className="flex size-4 shrink-0 items-center justify-center">
                <AnimatePresence mode="wait" initial={false}>
                  {isDone ? (
                    <motion.span
                      key="done"
                      initial={{ scale: 0.5, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                    >
                      <CheckCircle2 className="size-4 text-success" />
                    </motion.span>
                  ) : isActive ? (
                    <Loader2 className="size-4 animate-spin text-primary" />
                  ) : (
                    <span className="size-1.5 rounded-full bg-border" />
                  )}
                </AnimatePresence>
              </span>
              <span
                className={cn(
                  "text-sm",
                  isDone
                    ? "text-foreground"
                    : isActive
                      ? "font-medium text-foreground"
                      : "text-muted-foreground"
                )}
              >
                {step.label}
              </span>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
