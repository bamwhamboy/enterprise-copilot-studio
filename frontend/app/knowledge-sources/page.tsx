"use client";

import { Library } from "lucide-react";

import { useKnowledgeHubStore } from "@/store/knowledge-hub-store";
import { PageHeader } from "@/components/layout/page-header";
import { KnowledgeHubActions } from "@/components/knowledge-hub/knowledge-hub-actions";
import { KnowledgeHubMetrics } from "@/components/knowledge-hub/knowledge-hub-metrics";
import { CollectionsPanel } from "@/components/knowledge-hub/collections-panel";
import { KnowledgeTabs } from "@/components/knowledge-hub/knowledge-tabs";
import { KnowledgeSearchBar } from "@/components/knowledge-hub/knowledge-search-bar";
import { DocumentsTab } from "@/components/knowledge-hub/documents-tab";
import { DatabasesTab } from "@/components/knowledge-hub/databases-tab";
import { WebsitesTab } from "@/components/knowledge-hub/websites-tab";
import { ConnectorsTab } from "@/components/knowledge-hub/connectors-tab";
import { KnowledgeStatsPanel } from "@/components/knowledge-hub/knowledge-stats-panel";
import { DocumentDetailDrawer } from "@/components/knowledge-hub/document-detail-drawer";

export default function KnowledgeHubPage() {
  const activeTab = useKnowledgeHubStore((s) => s.activeTab);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Knowledge Hub"
        description="Manage and index enterprise knowledge sources used by your AI copilots."
        icon={Library}
        actions={<KnowledgeHubActions />}
      />

      <KnowledgeHubMetrics />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[260px_1fr_300px]">
        <div className="order-2 lg:order-1">
          <CollectionsPanel />
        </div>

        <div className="order-1 flex flex-col gap-4 lg:order-2">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <KnowledgeTabs />
            {activeTab === "documents" && <KnowledgeSearchBar />}
          </div>

          {activeTab === "documents" && <DocumentsTab />}
          {activeTab === "databases" && <DatabasesTab />}
          {activeTab === "websites" && <WebsitesTab />}
          {activeTab === "connectors" && <ConnectorsTab />}
        </div>

        <div className="order-3">
          <KnowledgeStatsPanel />
        </div>
      </div>

      <DocumentDetailDrawer />
    </div>
  );
}
