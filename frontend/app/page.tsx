"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  Database,
  FileStack,
  MessagesSquare,
  Sparkles,
  FilePlus2,
  FolderPlus,
  Loader2,
} from "lucide-react";

import type { StatCardData, ActivityItemData } from "@/types/dashboard";
import type { Copilot, CopilotCreatePayload } from "@/types/copilot";
import { useAuthStore } from "@/store/auth-store";
import { useChatStore } from "@/store/chat-store";
import { copilotsApi } from "@/lib/api/copilots";
import { knowledgeSourcesApi } from "@/lib/api/knowledge-sources";
import { organizationsApi } from "@/lib/api/organizations";
import { WelcomeBanner } from "@/components/dashboard/welcome-banner";
import { StatCard } from "@/components/dashboard/stat-card";
import { DashboardSection } from "@/components/dashboard/dashboard-section";
import { LivePlatformHealth } from "@/components/dashboard/live-platform-health";
import { CopilotCard } from "@/components/copilots/copilot-card";
import { CopilotFormDialog } from "@/components/copilots/copilot-form-dialog";
import { ActivityTimeline } from "@/components/dashboard/activity-timeline";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/error-state";

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days !== 1 ? "s" : ""} ago`;
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const chatSessions = useChatStore((s) => s.sessions);
  const queryClient = useQueryClient();
  const [editingCopilot, setEditingCopilot] = useState<Copilot | undefined>(undefined);
  const [formOpen, setFormOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const {
    data: copilots,
    isLoading: copilotsLoading,
    isError: copilotsError,
    refetch: refetchCopilots,
  } = useQuery({
    queryKey: ["copilots"],
    queryFn: copilotsApi.list,
  });
  const { data: sources, isLoading: sourcesLoading } = useQuery({
    queryKey: ["knowledge-sources"],
    queryFn: knowledgeSourcesApi.list,
  });
  const { data: organizations } = useQuery({
    queryKey: ["organizations"],
    queryFn: organizationsApi.list,
    // An organization's own name/id essentially never changes mid-session
    // -- no reason to re-verify this as eagerly as the default 60s.
    staleTime: 10 * 60 * 1000,
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

  const organization = organizations?.find((o) => o.id === user?.organization_id) ?? organizations?.[0];
  const totalDocuments = sources?.reduce((sum, s) => sum + s.documents.length, 0) ?? 0;
  const activeCopilots = copilots?.filter((c) => c.status === "active").length ?? 0;

  const draftCopilots = (copilots?.length ?? 0) - activeCopilots;

  const copilotTrendLabel = (() => {
    if (!copilots || copilots.length === 0) return undefined;
    if (activeCopilots === 0) return "All in draft";
    if (draftCopilots === 0) return "All active";
    return `${activeCopilots} active · ${draftCopilots} draft`;
  })();

  const kpiCards: StatCardData[] = [
    {
      id: "active-copilots",
      label: "Copilots",
      value: copilotsLoading ? "—" : String(copilots?.length ?? 0),
      icon: Bot,
      trendLabel: copilotTrendLabel,
      trendDirection: "flat",
    },
    {
      id: "knowledge-sources",
      label: "Knowledge Sources",
      value: sourcesLoading ? "—" : String(sources?.length ?? 0),
      icon: Database,
      trendDirection: "flat",
    },
    {
      id: "documents",
      label: "Documents",
      value: sourcesLoading ? "—" : String(totalDocuments),
      icon: FileStack,
      trendDirection: "flat",
    },
    {
      id: "chat-sessions",
      label: "Chat Sessions",
      value: String(chatSessions.length),
      icon: MessagesSquare,
      trendLabel: "This browser",
      trendDirection: "flat",
    },
  ];

  const activityItems: ActivityItemData[] = useMemo(() => {
    const events: (ActivityItemData & { sortKey: string })[] = [];
    copilots?.forEach((c) => {
      events.push({
        id: `copilot-${c.id}`,
        title: `Copilot "${c.name}" created`,
        description: `${c.domain.toUpperCase()} domain · ${c.knowledge_sources.length} knowledge source${c.knowledge_sources.length !== 1 ? "s" : ""} linked.`,
        timestamp: timeAgo(c.created_at),
        icon: Sparkles,
        status: "success",
        sortKey: c.created_at,
      });
    });
    sources?.forEach((s) => {
      events.push({
        id: `source-${s.id}`,
        title: `Knowledge source "${s.name}" created`,
        description: `${s.documents.length} document${s.documents.length !== 1 ? "s" : ""} in this source.`,
        timestamp: timeAgo(s.created_at),
        icon: FolderPlus,
        status: "info",
        sortKey: s.created_at,
      });
      s.documents.forEach((d) => {
        events.push({
          id: `doc-${d.id}`,
          title: `Document "${d.original_filename || d.name}" uploaded`,
          description: `${d.pages} page${d.pages !== 1 ? "s" : ""} · ${d.index_status === "INDEXED" ? "indexed" : "not yet indexed"}.`,
          timestamp: timeAgo(d.created_at),
          icon: FilePlus2,
          status: d.index_status === "INDEXED" ? "success" : "info",
          sortKey: d.created_at,
        });
      });
    });
    return events
      .sort((a, b) => new Date(b.sortKey).getTime() - new Date(a.sortKey).getTime())
      .slice(0, 6);
  }, [copilots, sources]);

  return (
    <div className="flex flex-col gap-8">
      <WelcomeBanner userName={user?.full_name || user?.email?.split("@")[0] || "there"} />

      {organization && user && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="flex items-center justify-between pt-6">
              <div>
                <p className="text-xs text-muted-foreground">Organization</p>
                <p className="text-sm font-semibold text-foreground">{organization.name}</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center justify-between pt-6">
              <div>
                <p className="text-xs text-muted-foreground">Current User</p>
                <p className="text-sm font-semibold text-foreground">
                  {user.full_name || user.email}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center justify-between pt-6">
              <div>
                <p className="text-xs text-muted-foreground">Role</p>
                <Badge variant="secondary" className="mt-1 capitalize">
                  {user.role.name.replace(/_/g, " ")}
                </Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <DashboardSection title="Key Metrics" description="Live snapshot across your copilot platform.">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {kpiCards.map((card) => (
            <StatCard key={card.id} data={card} />
          ))}
        </div>
      </DashboardSection>

      <DashboardSection title="Platform Health" description="Live status of the backend API.">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <LivePlatformHealth />
        </div>
      </DashboardSection>

      <div className="grid grid-cols-1 gap-8 xl:grid-cols-3">
        <div className="flex flex-col gap-8 xl:col-span-2">
          <DashboardSection
            title="Your Copilots"
            description="Jump back into a recently created copilot."
          >
            {copilotsError ? (
              <ErrorState onRetry={() => refetchCopilots()} showReturnToDashboard={false} />
            ) : copilotsLoading ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {[0, 1].map((i) => (
                  <Skeleton key={i} className="h-40 w-full rounded-xl" />
                ))}
              </div>
            ) : copilots && copilots.length > 0 ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {copilots.slice(0, 4).map((copilot) => (
                  <CopilotCard
                    key={copilot.id}
                    copilot={copilot}
                    onEdit={() => {
                      setEditingCopilot(copilot);
                      setFormOpen(true);
                    }}
                    onDelete={() => setDeletingId(copilot.id)}
                  />
                ))}
              </div>
            ) : (
              <Card>
                <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
                  <p className="text-sm font-medium text-foreground">No copilots yet</p>
                  <p className="text-xs text-muted-foreground">
                    Create your first copilot to see it here.
                  </p>
                </CardContent>
              </Card>
            )}
          </DashboardSection>
        </div>

        <DashboardSection title="Recent Activity" description="Latest changes across your workspace.">
          <Card>
            <CardContent className="pt-6">
              {activityItems.length > 0 ? (
                <ActivityTimeline items={activityItems} />
              ) : (
                <p className="py-6 text-center text-xs text-muted-foreground">
                  Activity will appear here once you create copilots and knowledge sources.
                </p>
              )}
            </CardContent>
          </Card>
        </DashboardSection>
      </div>

      <CopilotFormDialog
        key={editingCopilot?.id ?? "edit"}
        open={formOpen}
        onOpenChange={setFormOpen}
        copilot={editingCopilot}
        knowledgeSources={sources ?? []}
        onSubmit={(payload) => updateMutation.mutate(payload)}
        isSubmitting={updateMutation.isPending}
      />

      {deletingId && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-[2px]"
          onClick={() => setDeletingId(null)}
        >
          <Card className="w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
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
