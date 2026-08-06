"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles } from "lucide-react";

const FRIENDLY_MESSAGES = [
  "Preparing your copilot…",
  "Loading enterprise knowledge…",
  "Almost ready…",
];

/**
 * Inline, non-blocking "warming up" state shown inside the chat
 * interface itself while the copilot's data is still loading --
 * replaces what used to be a full-screen modal naming internal
 * implementation details ("Starting LangGraph...", etc.). Nothing
 * here is engineering-specific; it reads the way ChatGPT/Claude/
 * Copilot briefly show "Just a moment..." rather than a deployment log.
 */
export function CopilotWarmingUp() {
  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIndex((i) => Math.min(i + 1, FRIENDLY_MESSAGES.length - 1));
    }, 1100);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-[calc(100vh-6rem)] flex-col items-center justify-center gap-4">
      <motion.div
        animate={{ scale: [1, 1.05, 1] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
        className="flex size-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-[#5b7cfa] shadow-lg shadow-primary/25"
      >
        <Sparkles className="size-5 text-primary-foreground" />
      </motion.div>
      <AnimatePresence mode="wait">
        <motion.p
          key={messageIndex}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.25 }}
          className="text-sm text-muted-foreground"
        >
          {FRIENDLY_MESSAGES[messageIndex]}
        </motion.p>
      </AnimatePresence>
    </div>
  );
}
