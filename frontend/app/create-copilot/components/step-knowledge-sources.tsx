"use client";

import {
  FileText,
  Database,
  Globe,
  Share2,
  BookOpen,
  Snowflake,
  Server,
  Calendar,
  Check,
} from "lucide-react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";
import type { KnowledgeSourceOption } from "@/types/create-copilot";
import { useCreateCopilotStore } from "@/app/create-copilot/store/create-copilot-store";
import { Badge } from "@/components/ui/badge";

export const knowledgeSources: KnowledgeSourceOption[] = [
  {
    id: "pdf-documents",
    label: "PDF Documents",
    description: "Policies, handbooks, and forms stored as PDFs.",
    icon: FileText,
    status: "available",
  },
  {
    id: "sql-database",
    label: "SQL Database",
    description: "Structured HR records from a relational database.",
    icon: Database,
    status: "available",
  },
  {
    id: "website",
    label: "Website",
    description: "Public or internal HR portal pages.",
    icon: Globe,
    status: "available",
  },
  {
    id: "sharepoint",
    label: "SharePoint",
    description: "Documents and lists from SharePoint sites.",
    icon: Share2,
    status: "coming-soon",
  },
  {
    id: "confluence",
    label: "Confluence",
    description: "Team wikis and knowledge base pages.",
    icon: BookOpen,
    status: "coming-soon",
  },
  {
    id: "snowflake",
    label: "Snowflake",
    description: "Data warehouse tables and views.",
    icon: Snowflake,
    status: "coming-soon",
  },
  {
    id: "sap",
    label: "SAP",
    description: "Core HR and payroll records from SAP.",
    icon: Server,
    status: "coming-soon",
  },
  {
    id: "workday",
    label: "Workday",
    description: "Employee, benefits, and leave data.",
    icon: Calendar,
    status: "coming-soon",
  },
];

export function StepKnowledgeSources() {
  const { knowledgeSourceIds, toggleKnowledgeSource } =
    useCreateCopilotStore();

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Select one or more knowledge sources this copilot should retrieve
        answers from. You can add more sources later.
      </p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {knowledgeSources.map((source) => {
          const isAvailable = source.status === "available";
          const isSelected = knowledgeSourceIds.includes(source.id);

          return (
            <motion.button
              key={source.id}
              type="button"
              disabled={!isAvailable}
              onClick={() => isAvailable && toggleKnowledgeSource(source.id)}
              whileHover={isAvailable ? { y: -2 } : undefined}
              className={cn(
                "relative flex flex-col gap-3 rounded-xl border border-border bg-card p-4 text-left transition-all",
                isAvailable && "cursor-pointer hover:border-primary/40 hover:shadow-md",
                isSelected && "border-primary bg-primary/5 ring-2 ring-primary/20",
                !isAvailable && "cursor-not-allowed opacity-50"
              )}
            >
              <div className="flex items-start justify-between">
                <div className="relative">
                  <div
                    className={cn(
                      "flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary",
                      !isAvailable && "grayscale"
                    )}
                  >
                    <source.icon className="size-4" />
                  </div>
                  {isSelected && (
                    <span className="absolute -right-1.5 -top-1.5 flex size-4 items-center justify-center rounded-full bg-primary text-primary-foreground ring-2 ring-card">
                      <Check className="size-2.5" />
                    </span>
                  )}
                </div>
                <Badge variant={isAvailable ? "success" : "secondary"}>
                  {isAvailable ? "Available" : "Coming Soon"}
                </Badge>
              </div>

              <div className="flex flex-col gap-0.5">
                <span className="text-sm font-semibold text-foreground">
                  {source.label}
                </span>
                <span className="text-xs text-muted-foreground">
                  {source.description}
                </span>
              </div>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
