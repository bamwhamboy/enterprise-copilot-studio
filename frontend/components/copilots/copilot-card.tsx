"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { MessageSquare, MoreVertical, Pencil, Trash2, Database } from "lucide-react";

import type { Copilot } from "@/types/copilot";
import { COPILOT_DOMAIN_LABELS, COPILOT_STATUS_LABELS } from "@/types/copilot";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
      transition={{ duration: 0.25 }}
    >
      <Card className="group relative overflow-hidden transition-shadow hover:shadow-md">
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

          <Button asChild size="sm" className="w-full">
            <Link href={`/copilots/${copilot.id}/chat`}>
              Launch Copilot
              <MessageSquare className="size-3.5" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    </motion.div>
  );
}
