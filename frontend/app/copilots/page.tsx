"use client";

import { useState } from "react";
import Link from "next/link";
import { Bot, Plus, Loader2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { copilotsApi } from "@/lib/api/copilots";
import { knowledgeSourcesApi } from "@/lib/api/knowledge-sources";
import type { Copilot, CopilotCreatePayload } from "@/types/copilot";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CopilotCard } from "@/components/copilots/copilot-card";
import { CopilotFormDialog } from "@/components/copilots/copilot-form-dialog";
import { ErrorState } from "@/components/shared/error-state";

export default function CopilotsPage() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [editingCopilot, setEditingCopilot] = useState<Copilot | undefined>(undefined);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data: copilots, isLoading, isError, refetch } = useQuery({
    queryKey: ["copilots"],
    queryFn: copilotsApi.list,
  });

  const { data: knowledgeSources } = useQuery({
    queryKey: ["knowledge-sources"],
    queryFn: knowledgeSourcesApi.list,
  });

  const createMutation = useMutation({
    mutationFn: (payload: CopilotCreatePayload) => copilotsApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["copilots"] });
      setFormOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: CopilotCreatePayload) =>
      copilotsApi.update(editingCopilot!.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["copilots"] });
      setFormOpen(false);
      setEditingCopilot(undefined);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => copilotsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["copilots"] });
      setDeletingId(null);
    },
  });

  function openEdit(copilot: Copilot) {
    setEditingCopilot(copilot);
    setFormOpen(true);
  }

  function handleSubmit(payload: CopilotCreatePayload) {
    if (editingCopilot) {
      updateMutation.mutate(payload);
    } else {
      createMutation.mutate(payload);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Copilots"
        description="Create, configure, and launch enterprise AI copilots grounded in your knowledge sources."
        icon={Bot}
        actions={
          <Button asChild>
            <Link href="/create-copilot">
              <Plus className="size-4" />
              Create Copilot
            </Link>
          </Button>
        }
      />

      {isError ? (
        <ErrorState onRetry={() => refetch()} showReturnToDashboard={false} />
      ) : isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Card key={i}>
              <CardContent className="flex flex-col gap-4 pt-6">
                <Skeleton className="size-10 rounded-xl" />
                <Skeleton className="h-4 w-2/3 rounded-md" />
                <Skeleton className="h-3 w-full rounded-md" />
                <Skeleton className="h-8 w-full rounded-md" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : copilots && copilots.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {copilots.map((copilot) => (
            <CopilotCard
              key={copilot.id}
              copilot={copilot}
              onEdit={() => openEdit(copilot)}
              onDelete={() => setDeletingId(copilot.id)}
            />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-3 py-24 text-center">
            <div className="flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary">
              <Bot className="size-6" />
            </div>
            <p className="text-sm font-medium text-foreground">No copilots yet</p>
            <p className="max-w-sm text-xs text-muted-foreground">
              Create your first copilot and link it to a knowledge source to start chatting.
            </p>
            <Button asChild size="sm" className="mt-1">
              <Link href="/create-copilot">
                <Plus className="size-3.5" />
                Create Copilot
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}

      <CopilotFormDialog
        key={editingCopilot?.id ?? "create"}
        open={formOpen}
        onOpenChange={setFormOpen}
        copilot={editingCopilot}
        knowledgeSources={knowledgeSources ?? []}
        onSubmit={handleSubmit}
        isSubmitting={createMutation.isPending || updateMutation.isPending}
      />

      {deletingId && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-[2px]"
          onClick={() => setDeletingId(null)}
        >
          <Card
            className="w-full max-w-sm"
            onClick={(e) => e.stopPropagation()}
          >
            <CardContent className="flex flex-col gap-4 pt-6">
              <div>
                <p className="text-sm font-semibold text-foreground">Delete this copilot?</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  This can&apos;t be undone. Conversations tied to it will remain, but it can no
                  longer be launched.
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
