"use client";

import { useState } from "react";
import { Library, Plus, Loader2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { knowledgeSourcesApi } from "@/lib/api/knowledge-sources";
import { invalidateKnowledgeData } from "@/lib/query-invalidation";
import type { KnowledgeSourceCreatePayload } from "@/types/knowledge-source";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { SourceCard } from "@/components/knowledge-sources/source-card";
import { CreateSourceDialog } from "@/components/knowledge-sources/create-source-dialog";

export default function KnowledgeSourcesPage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data: sources, isLoading } = useQuery({
    queryKey: ["knowledge-sources"],
    queryFn: knowledgeSourcesApi.list,
    refetchInterval: (query) => {
      const list = query.state.data ?? [];
      const hasInFlightDocument = list.some((source) =>
        source.documents.some(
          (doc) =>
            doc.processing_status === "UPLOADED" ||
            doc.processing_status === "PROCESSING" ||
            doc.index_status === "INDEXING"
        )
      );
      return hasInFlightDocument ? 3000 : false;
    },
  });

  const createMutation = useMutation({
    mutationFn: (payload: KnowledgeSourceCreatePayload) => knowledgeSourcesApi.create(payload),
    onSuccess: () => {
      invalidateKnowledgeData(queryClient);
      setCreateOpen(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => knowledgeSourcesApi.remove(id),
    onSuccess: () => {
      invalidateKnowledgeData(queryClient);
      setDeletingId(null);
    },
  });

  const totalDocuments = sources?.reduce((sum, s) => sum + s.documents.length, 0) ?? 0;
  const totalIndexed =
    sources?.reduce(
      (sum, s) => sum + s.documents.filter((d) => d.index_status === "INDEXED").length,
      0
    ) ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Knowledge Sources"
        description="Manage the documents your copilots retrieve from and cite."
        icon={Library}
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="size-4" />
            Create Knowledge Source
          </Button>
        }
      />

      {sources && sources.length > 0 && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="pt-6">
              <p className="text-2xl font-semibold text-foreground">{sources.length}</p>
              <p className="text-xs text-muted-foreground">Knowledge sources</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-2xl font-semibold text-foreground">{totalDocuments}</p>
              <p className="text-xs text-muted-foreground">Total documents</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-2xl font-semibold text-foreground">{totalIndexed}</p>
              <p className="text-xs text-muted-foreground">Indexed documents</p>
            </CardContent>
          </Card>
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Card key={i}>
              <CardContent className="flex flex-col gap-4 pt-6">
                <Skeleton className="size-10 rounded-xl" />
                <Skeleton className="h-4 w-2/3 rounded-md" />
                <Skeleton className="h-3 w-1/2 rounded-md" />
                <Skeleton className="h-8 w-full rounded-md" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : sources && sources.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {sources.map((source) => (
            <SourceCard key={source.id} source={source} onDelete={() => setDeletingId(source.id)} />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-3 py-24 text-center">
            <div className="flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary">
              <Library className="size-6" />
            </div>
            <p className="text-sm font-medium text-foreground">No knowledge sources yet</p>
            <p className="max-w-sm text-xs text-muted-foreground">
              Create one and upload documents to start grounding your copilots in real content.
            </p>
            <Button onClick={() => setCreateOpen(true)} size="sm" className="mt-1">
              <Plus className="size-3.5" />
              Create Knowledge Source
            </Button>
          </CardContent>
        </Card>
      )}

      <CreateSourceDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onSubmit={(payload) => createMutation.mutate(payload)}
        isSubmitting={createMutation.isPending}
      />

      {deletingId && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-[2px]"
          onClick={() => setDeletingId(null)}
        >
          <Card className="w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
            <CardContent className="flex flex-col gap-4 pt-6">
              <div>
                <p className="text-sm font-semibold text-foreground">Delete this knowledge source?</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  All of its documents will be removed. Copilots linked to it will no longer be
                  grounded in this content. This can&apos;t be undone.
                </p>
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" size="sm" onClick={() => setDeletingId(null)}>
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => deleteMutation.mutate(deletingId)}
                  disabled={deleteMutation.isPending}
                >
                  {deleteMutation.isPending && <Loader2 className="size-3.5 animate-spin" />}
                  Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
