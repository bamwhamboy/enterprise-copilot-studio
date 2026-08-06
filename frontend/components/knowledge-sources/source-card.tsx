"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Database, FileText, MoreVertical, Trash2, CheckCircle2 } from "lucide-react";

import type { ApiKnowledgeSource } from "@/types/knowledge-source";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const SOURCE_TYPE_LABELS: Record<ApiKnowledgeSource["source_type"], string> = {
  documents: "Documents",
  database: "Database",
  website: "Website",
  connector: "Connector",
};

function statusVariant(status: ApiKnowledgeSource["status"]) {
  if (status === "active" || status === "connected") return "success" as const;
  if (status === "syncing" || status === "pending") return "warning" as const;
  return "secondary" as const;
}

interface SourceCardProps {
  source: ApiKnowledgeSource;
  onDelete: () => void;
}

export function SourceCard({ source, onDelete }: SourceCardProps) {
  const indexedCount = source.documents.filter((d) => d.index_status === "INDEXED").length;

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <Card className="group relative overflow-hidden transition-shadow hover:shadow-md">
        <CardContent className="flex h-full flex-col gap-4 pt-6">
          <div className="flex items-start justify-between">
            <div className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary">
              <Database className="size-5" />
            </div>
            <div className="flex items-center gap-1">
              <Badge variant={statusVariant(source.status)} className="capitalize">
                {source.status}
              </Badge>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="size-7">
                    <MoreVertical className="size-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem variant="destructive" onSelect={onDelete}>
                    <Trash2 className="size-3.5" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          <div className="flex flex-1 flex-col gap-1">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {SOURCE_TYPE_LABELS[source.source_type]}
            </span>
            <Link href={`/knowledge-sources/${source.id}`} className="text-sm font-semibold text-foreground hover:text-primary">
              {source.name}
            </Link>
          </div>

          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <FileText className="size-3.5" />
              {source.documents.length} document{source.documents.length !== 1 ? "s" : ""}
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="size-3.5" />
              {indexedCount} indexed
            </span>
          </div>

          <Button asChild variant="outline" size="sm" className="w-full">
            <Link href={`/knowledge-sources/${source.id}`}>Manage documents</Link>
          </Button>
        </CardContent>
      </Card>
    </motion.div>
  );
}
