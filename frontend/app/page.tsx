"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bot,
  Database,
  FileStack,
  MessagesSquare,
  Users,
  Landmark,
  Building2,
  Laptop,
  Sparkles,
  FilePlus2,
  FolderPlus,
} from "lucide-react";

import type { StatCardData, MarketplaceCopilotData, ActivityItemData } from "@/types/dashboard";
import { useAuthStore } from "@/store/auth-store";
import { useChatStore } from "@/store/chat-store";
import { copilotsApi } from "@/lib/api/copilots";
import { knowledgeSourcesApi } from "@/lib/api/knowledge-sources";
import { organizationsApi } from "@/lib/api/organizations";
import { WelcomeBanner } from "@/components/dashboard/welcome-banner";
import { StatCard } from "@/components/dashboard/stat-card";
import { DashboardSection } from "@/components/dashboard/dashboard-section";
import { LivePlatformHealth } from "@/components/dashboard/live-platform-health";
import { MarketplaceCopilotCard } from "@/components/dashboard/marketplace-copilot-card";
import { ActivityTimeline } from "@/components/dashboard/activity-timeline";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

const CATEGORY_ICONS: Record<string, typeof Users> = {
  hr: Users,
  finance: Landmark,
  procurement: Building2,
  it: Laptop,
};

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

  const { data: copilots, isLoading: copilotsLoading } = useQuery({
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
  });

  const organization = organizations?.find((o) => o.id === user?.organization_id) ?? organizations?.[0];
  const totalDocuments = sources?.reduce((sum, s) => sum + s.documents.length, 0) ?? 0;
  const activeCopilots = copilots?.filter((c) => c.status === "active").length ?? 0;

  const kpiCards: StatCardData[] = [
    {
      id: "active-copilots",
      label: "Active Copilots",
      value: copilotsLoading ? "—" : String(activeCopilots),
      icon: Bot,
      trendLabel: copilots ? `${copilots.length} total` : undefined,
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

  const marketplaceCopilots: MarketplaceCopilotData[] = useMemo(() => {
    if (!copilots || copilots.length === 0) return [];
    return copilots.slice(0, 4).map((copilot) => ({
      id: copilot.id,
      name: copilot.name,
      description: copilot.description || `${copilot.domain.toUpperCase()} copilot`,
      category: copilot.domain,
      icon: CATEGORY_ICONS[copilot.domain] ?? Bot,
      status: copilot.status === "active" ? "available" : "coming-soon",
      href: copilot.status === "active" ? `/copilots/${copilot.id}/chat` : "/copilots",
    }));
  }, [copilots]);

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
            {copilotsLoading ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {[0, 1].map((i) => (
                  <Skeleton key={i} className="h-40 w-full rounded-xl" />
                ))}
              </div>
            ) : marketplaceCopilots.length > 0 ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {marketplaceCopilots.map((copilot) => (
                  <MarketplaceCopilotCard key={copilot.id} data={copilot} />
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
    </div>
  );
}
