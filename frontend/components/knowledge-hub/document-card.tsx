"use client";

import { FileText, Eye, RefreshCcw, Trash2, Loader2 } from "lucide-react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";
import type { KnowledgeDocument, DocumentStatus } from "@/types/knowledge-hub";
import { useKnowledgeHubStore } from "@/store/knowledge-hub-store";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const statusConfig: Record<
  DocumentStatus,
  { label: string; variant: "success" | "warning" | "secondary" }
> = {
  indexed: { label: "Indexed", variant: "success" },
  processing: { label: "Processing", variant: "warning" },
  pending: { label: "Pending", variant: "secondary" },
};

export function DocumentCard({ document }: { document: KnowledgeDocument }) {
  const { openDocument, reindexDocument, deleteDocument } = useKnowledgeHubStore();
  const status = statusConfig[document.status];
  const isProcessing = document.status === "processing";

  return (
    <motion.div layout whileHover={{ y: -2 }}>
      <Card className="h-full transition-shadow hover:shadow-md">
        <CardContent className="flex h-full flex-col gap-4 pt-6">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-3">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary">
                <FileText className="size-4" />
              </div>
              <span className="text-sm font-semibold text-foreground">
                {document.name}
              </span>
            </div>
            <Badge variant={status.variant} className="shrink-0">
              {isProcessing && <Loader2 className="size-3 animate-spin" />}
              {status.label}
            </Badge>
          </div>

          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="flex flex-col gap-0.5">
              <span className="text-xs text-muted-foreground">Pages</span>
              <span className="text-sm font-medium text-foreground">
                {document.pages}
              </span>
            </div>
            <div className="flex flex-col gap-0.5 border-x border-border">
              <span className="text-xs text-muted-foreground">Chunks</span>
              <span className="text-sm font-medium text-foreground">
                {document.chunks || "—"}
              </span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-xs text-muted-foreground">Embeddings</span>
              <span className="text-sm font-medium text-foreground">
                {document.embeddings || "—"}
              </span>
            </div>
          </div>

          <span className="text-xs text-muted-foreground">
            Uploaded {document.uploadedAt}
          </span>

          <Separator className="mt-auto" />

          <div className="flex items-center gap-1.5">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => openDocument(document.id)}
            >
              <Eye className="size-3.5" />
              Preview
            </Button>
            <Button
              variant="outline"
              size="sm"
              className={cn("flex-1", isProcessing && "pointer-events-none opacity-60")}
              onClick={() => reindexDocument(document.id)}
              disabled={isProcessing}
            >
              <RefreshCcw className={cn("size-3.5", isProcessing && "animate-spin")} />
              Re-index
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="text-destructive hover:bg-destructive/10 hover:text-destructive"
              onClick={() => deleteDocument(document.id)}
              aria-label="Delete document"
            >
              <Trash2 className="size-3.5" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
