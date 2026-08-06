"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, FileText, Loader2, Sparkles, Trash2 } from "lucide-react";

import { knowledgeSourcesApi } from "@/lib/api/knowledge-sources";
import { documentsApi } from "@/lib/api/documents";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { DocumentDropzone } from "@/components/knowledge-sources/document-dropzone";
import {
  ProcessingStatusBadge,
  IndexStatusBadge,
} from "@/components/shared/document-status-badges";

interface UploadTask {
  id: string;
  file: File;
  progress: number;
  status: "uploading" | "indexing" | "done" | "error";
  errorMessage?: string;
}

export function KnowledgeSourceDetail({ knowledgeSourceId }: { knowledgeSourceId: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [uploads, setUploads] = useState<UploadTask[]>([]);

  const { data: source, isLoading } = useQuery({
    queryKey: ["knowledge-source", knowledgeSourceId],
    queryFn: () => knowledgeSourcesApi.get(knowledgeSourceId),
  });

  const deleteDocMutation = useMutation({
    mutationFn: (documentId: string) => documentsApi.remove(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-source", knowledgeSourceId] });
    },
  });

  async function handleFilesSelected(files: File[]) {
    for (const file of files) {
      const taskId = `${file.name}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      setUploads((prev) => [...prev, { id: taskId, file, progress: 0, status: "uploading" }]);

      try {
        const document = await knowledgeSourcesApi.uploadDocument(
          knowledgeSourceId,
          file,
          (percent) =>
            setUploads((prev) =>
              prev.map((t) => (t.id === taskId ? { ...t, progress: percent } : t))
            )
        );

        setUploads((prev) =>
          prev.map((t) => (t.id === taskId ? { ...t, status: "indexing", progress: 100 } : t))
        );

        await knowledgeSourcesApi.indexDocument(document.id);

        setUploads((prev) => prev.map((t) => (t.id === taskId ? { ...t, status: "done" } : t)));
        queryClient.invalidateQueries({ queryKey: ["knowledge-source", knowledgeSourceId] });
      } catch (err) {
        const message = (err as { message?: string })?.message ?? "Upload failed.";
        setUploads((prev) =>
          prev.map((t) => (t.id === taskId ? { ...t, status: "error", errorMessage: message } : t))
        );
      }
    }
  }

  async function handleIndexNow(documentId: string) {
    await knowledgeSourcesApi.indexDocument(documentId);
    queryClient.invalidateQueries({ queryKey: ["knowledge-source", knowledgeSourceId] });
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-10 w-64 rounded-lg" />
        <Skeleton className="h-40 w-full rounded-xl" />
      </div>
    );
  }

  if (!source) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-24 text-center">
        <p className="text-sm font-medium text-foreground">Knowledge source not found.</p>
        <Button variant="outline" onClick={() => router.push("/knowledge-sources")}>
          Back to Knowledge Sources
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={source.name}
        description={`${source.documents.length} document${source.documents.length !== 1 ? "s" : ""} in this knowledge source`}
        icon={FileText}
        actions={
          <Button variant="outline" onClick={() => router.push("/knowledge-sources")}>
            <ArrowLeft className="size-4" />
            Back
          </Button>
        }
      />

      <Card>
        <CardContent className="flex flex-col gap-4 pt-6">
          <DocumentDropzone onFilesSelected={handleFilesSelected} />

          {uploads.length > 0 && (
            <div className="flex flex-col gap-2">
              {uploads.map((task) => (
                <div
                  key={task.id}
                  className="flex items-center gap-3 rounded-lg border border-border px-3 py-2.5"
                >
                  <FileText className="size-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium text-foreground">
                      {task.file.name}
                    </p>
                    {task.status === "uploading" && (
                      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-primary transition-all"
                          style={{ width: `${task.progress}%` }}
                        />
                      </div>
                    )}
                    {task.status === "error" && (
                      <p className="mt-0.5 text-[11px] text-destructive">{task.errorMessage}</p>
                    )}
                  </div>
                  <div className="shrink-0 text-xs text-muted-foreground">
                    {task.status === "uploading" && `${task.progress}%`}
                    {task.status === "indexing" && (
                      <span className="flex items-center gap-1 text-primary">
                        <Sparkles className="size-3 animate-pulse" />
                        Indexing…
                      </span>
                    )}
                    {task.status === "done" && <span className="text-success">Done</span>}
                    {task.status === "error" && <span className="text-destructive">Failed</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {source.documents.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-2 py-16 text-center">
            <p className="text-sm font-medium text-foreground">No documents yet</p>
            <p className="text-xs text-muted-foreground">
              Upload a PDF above to get started.
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y divide-border">
              {source.documents.map((doc) => (
                <div key={doc.id} className="flex items-center gap-3 px-4 py-3">
                  <FileText className="size-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {doc.original_filename || doc.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {doc.pages} page{doc.pages !== 1 ? "s" : ""} · {doc.chunks} chunk
                      {doc.chunks !== 1 ? "s" : ""}
                    </p>
                  </div>
                  <ProcessingStatusBadge status={doc.processing_status} />
                  <IndexStatusBadge status={doc.index_status} />
                  {doc.processing_status === "READY" &&
                    (doc.index_status === "NOT_INDEXED" || doc.index_status === "FAILED") && (
                      <Button size="sm" variant="outline" onClick={() => handleIndexNow(doc.id)}>
                        Index now
                      </Button>
                    )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-8 text-muted-foreground hover:text-destructive"
                    onClick={() => deleteDocMutation.mutate(doc.id)}
                    aria-label="Delete document"
                  >
                    {deleteDocMutation.isPending && deleteDocMutation.variables === doc.id ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="size-3.5" />
                    )}
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
