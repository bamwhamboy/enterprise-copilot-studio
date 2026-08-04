"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X, FileText, Layers, Atom, CalendarClock, CheckCircle2 } from "lucide-react";

import { useKnowledgeHubStore } from "@/store/knowledge-hub-store";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

export function DocumentDetailDrawer() {
  const { documents, activeDocumentId, isDrawerOpen, closeDrawer } =
    useKnowledgeHubStore();

  const document = documents.find((d) => d.id === activeDocumentId);

  return (
    <DialogPrimitive.Root open={isDrawerOpen} onOpenChange={closeDrawer}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          className={
            "fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] " +
            "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0"
          }
        />
        <DialogPrimitive.Content
          className={
            "fixed inset-y-0 right-0 z-50 flex h-full w-full max-w-sm flex-col gap-6 border-l border-border bg-card p-6 shadow-xl outline-none " +
            "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right"
          }
        >
          <DialogPrimitive.Title className="sr-only">
            Document details
          </DialogPrimitive.Title>

          {document && (
            <>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary">
                    <FileText className="size-5" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold leading-tight text-foreground">
                      {document.name}
                    </p>
                    <p className="text-xs text-muted-foreground">PDF Document</p>
                  </div>
                </div>
                <DialogPrimitive.Close className="rounded-md p-1 text-muted-foreground opacity-70 transition-opacity hover:bg-accent hover:opacity-100">
                  <X className="size-4" />
                  <span className="sr-only">Close</span>
                </DialogPrimitive.Close>
              </div>

              <div className="flex items-center gap-2">
                <Badge variant={document.status === "indexed" ? "success" : "warning"}>
                  {document.status === "indexed" && (
                    <CheckCircle2 className="size-3" />
                  )}
                  {document.status === "indexed"
                    ? "Indexed"
                    : document.status === "processing"
                    ? "Processing"
                    : "Pending"}
                </Badge>
              </div>

              <Separator />

              <div className="flex flex-col gap-4">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Document Metadata
                </p>

                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center gap-2.5">
                    <div className="flex size-8 items-center justify-center rounded-lg bg-muted text-foreground/70">
                      <FileText className="size-3.5" />
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Pages</p>
                      <p className="text-sm font-medium text-foreground">
                        {document.pages}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5">
                    <div className="flex size-8 items-center justify-center rounded-lg bg-muted text-foreground/70">
                      <Layers className="size-3.5" />
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Chunks</p>
                      <p className="text-sm font-medium text-foreground">
                        {document.chunks || "—"}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5">
                    <div className="flex size-8 items-center justify-center rounded-lg bg-muted text-foreground/70">
                      <Atom className="size-3.5" />
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Embeddings</p>
                      <p className="text-sm font-medium text-foreground">
                        {document.embeddings || "—"}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5">
                    <div className="flex size-8 items-center justify-center rounded-lg bg-muted text-foreground/70">
                      <CalendarClock className="size-3.5" />
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Uploaded</p>
                      <p className="text-sm font-medium text-foreground">
                        {document.uploadedAt}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <Separator />

              <div className="flex flex-col gap-2 rounded-lg bg-muted/40 p-3">
                <p className="text-xs font-medium text-foreground">
                  Last indexed
                </p>
                <p className="text-xs text-muted-foreground">
                  {document.status === "indexed"
                    ? "5 minutes ago via Hierarchical Hybrid RAG"
                    : "Not yet indexed"}
                </p>
              </div>
            </>
          )}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
