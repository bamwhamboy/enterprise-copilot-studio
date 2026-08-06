"use client";

import { motion } from "framer-motion";
import { Sparkles, ShieldCheck, Workflow, Database } from "lucide-react";

const highlights = [
  {
    icon: Workflow,
    title: "LangGraph-orchestrated copilots",
    description: "Multi-step retrieval, grounding, and citation in one workflow.",
  },
  {
    icon: Database,
    title: "Hybrid Hierarchical RAG",
    description: "Semantic + BM25 retrieval over your enterprise knowledge.",
  },
  {
    icon: ShieldCheck,
    title: "Enterprise-grade security",
    description: "JWT auth, role-based access, and organization isolation.",
  },
];

/**
 * Shared branding panel for the auth screens (login, register) -- a
 * single source of truth so both pages stay visually identical rather
 * than two copies drifting apart over time.
 */
export function AuthBrandingPanel({
  headline,
}: {
  headline: string;
}) {
  return (
    <div className="relative hidden overflow-hidden bg-gradient-to-br from-[#1a1730] via-[#221c42] to-[#171325] lg:flex lg:flex-col lg:justify-between lg:p-12">
      <div className="pointer-events-none absolute inset-0 opacity-40">
        <div className="absolute -top-24 -left-24 size-96 rounded-full bg-primary/30 blur-3xl" />
        <div className="absolute -bottom-32 -right-16 size-96 rounded-full bg-[#5b7cfa]/30 blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative flex items-center gap-2.5"
      >
        <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-[#5b7cfa] shadow-lg shadow-primary/30">
          <Sparkles className="size-[18px] text-primary-foreground" />
        </div>
        <span className="text-base font-semibold tracking-tight text-white">
          Enterprise Copilot Studio
        </span>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1 }}
        className="relative flex flex-col gap-10"
      >
        <div>
          <h1 className="max-w-md text-3xl font-semibold leading-tight tracking-tight text-white">
            {headline}
          </h1>
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-white/60">
            One platform for retrieval-grounded chat, knowledge management, and
            enterprise-grade governance — built on your own data.
          </p>
        </div>

        <div className="flex flex-col gap-5">
          {highlights.map((item, index) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: 0.2 + index * 0.08 }}
              className="flex items-start gap-3.5"
            >
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-white/10 text-white backdrop-blur-sm">
                <item.icon className="size-4" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">{item.title}</p>
                <p className="mt-0.5 text-xs leading-relaxed text-white/50">
                  {item.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      <p className="relative text-xs text-white/35">
        © {new Date().getFullYear()} Enterprise Copilot Studio. All rights reserved.
      </p>
    </div>
  );
}
