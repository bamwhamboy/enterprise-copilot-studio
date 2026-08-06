"use client";

import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

interface SuggestedPromptsProps {
  copilotName: string;
  prompts: string[];
  onSelect: (prompt: string) => void;
}

export function SuggestedPrompts({ copilotName, prompts, onSelect }: SuggestedPromptsProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 px-6 text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-[#5b7cfa] shadow-lg shadow-primary/25"
      >
        <Sparkles className="size-6 text-primary-foreground" />
      </motion.div>
      <div>
        <h2 className="text-lg font-semibold text-foreground">
          Ask {copilotName} anything
        </h2>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          Responses are grounded in your organization&apos;s knowledge sources, with
          citations for every answer.
        </p>
      </div>
      <div className="grid w-full max-w-lg grid-cols-1 gap-2 sm:grid-cols-2">
        {prompts.map((prompt, index) => (
          <motion.button
            key={prompt}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.06 }}
            onClick={() => onSelect(prompt)}
            className="rounded-xl border border-border bg-card px-4 py-3 text-left text-sm text-foreground shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md"
          >
            {prompt}
          </motion.button>
        ))}
      </div>
    </div>
  );
}
