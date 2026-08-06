"use client";

import { motion } from "framer-motion";
import { MoreVertical, Pencil, Trash2, Database, Calendar, ShieldCheck, Quote, Brain } from "lucide-react";

import type { Copilot } from "@/types/copilot";
import { COPILOT_DOMAIN_LABELS, COPILOT_STATUS_LABELS } from "@/types/copilot";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LaunchCopilotButton } from "@/components/shared/launch-copilot-button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

function statusVariant(status: Copilot["status"]) {
  if (status === "active") return "success" as const;
  if (status === "archived") return "secondary" as const;
  return "warning" as const;
}

function getInitials(name: string) {
  return name
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function formatCreatedAt(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

interface CopilotCardProps {
  copilot: Copilot;
  onEdit: () => void;
  onDelete: () => void;
}

export function CopilotCard({ copilot, onEdit, onDelete }: CopilotCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -3 }}
      transition={{ duration: 0.25 }}
    >
      <Card className="group relative overflow-hidden transition-shadow duration-200 hover:shadow-lg hover:shadow-primary/5">
        <CardContent className="flex h-full flex-col gap-4 pt-6">
          <div className="flex items-start justify-between">
            <div className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-sm font-semibold text-primary">
              {getInitials(copilot.name)}
            </div>
            <div className="flex items-center gap-1">
              <Badge variant={statusVariant(copilot.status)}>
                {COPILOT_STATUS_LABELS[copilot.status]}
              </Badge>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="size-7">
                    <MoreVertical className="size-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onSelect={onEdit}>
                    <Pencil className="size-3.5" />
                    Edit
                  </DropdownMenuItem>
                  <DropdownMenuItem variant="destructive" onSelect={onDelete}>
                    <Trash2 className="size-3.5" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          <div className="flex flex-1 flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {COPILOT_DOMAIN_LABELS[copilot.domain]}
            </span>
            <span className="text-sm font-semibold text-foreground">{copilot.name}</span>
            <p className="line-clamp-2 text-xs text-muted-foreground">
              {copilot.description || "No description yet."}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="outline" className="font-mono text-[10px]">
              {copilot.model}
            </Badge>
            {copilot.knowledge_sources.length > 0 && (
              <Badge variant="outline" className="gap-1 text-[10px]">
                <Database className="size-2.5" />
                {copilot.knowledge_sources.length}
              </Badge>
            )}
          </div>

          <div className="flex items-center justify-between border-t border-border pt-3">
            <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <Calendar className="size-3" />
              {formatCreatedAt(copilot.created_at)}
            </span>
            <div
              className="flex items-center gap-1.5 text-muted-foreground/60"
              title="Guardrails, Citations, and Conversation Memory are enabled for every copilot"
            >
              <ShieldCheck className="size-3" />
              <Quote className="size-3" />
              <Brain className="size-3" />
            </div>
          </div>

          <LaunchCopilotButton
            copilotId={copilot.id}
            copilotName={copilot.name}
            className="w-full"
          />
        </CardContent>
      </Card>
    </motion.div>
  );
}
