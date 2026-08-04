"use client";

import { FileText, Database, Globe, Plug } from "lucide-react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";
import { useKnowledgeHubStore } from "@/store/knowledge-hub-store";
import type { KnowledgeHubTab } from "@/types/knowledge-hub";

const tabs: { id: KnowledgeHubTab; label: string; icon: typeof FileText }[] = [
  { id: "documents", label: "Documents", icon: FileText },
  { id: "databases", label: "Databases", icon: Database },
  { id: "websites", label: "Websites", icon: Globe },
  { id: "connectors", label: "Enterprise Connectors", icon: Plug },
];

export function KnowledgeTabs() {
  const { activeTab, setActiveTab } = useKnowledgeHubStore();

  return (
    <div className="relative flex w-full gap-1 overflow-x-auto rounded-xl border border-border bg-muted/40 p-1">
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;

        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "relative flex shrink-0 items-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors",
              isActive ? "text-foreground" : "text-muted-foreground hover:text-foreground"
            )}
          >
            {isActive && (
              <motion.span
                layoutId="knowledge-tab-active"
                className="absolute inset-0 rounded-lg bg-card shadow-sm"
                transition={{ type: "spring", stiffness: 380, damping: 32 }}
              />
            )}
            <tab.icon className="relative z-10 size-4" />
            <span className="relative z-10 whitespace-nowrap">{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}
