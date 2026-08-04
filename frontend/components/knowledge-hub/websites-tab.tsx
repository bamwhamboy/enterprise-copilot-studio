"use client";

import { useKnowledgeHubStore } from "@/store/knowledge-hub-store";
import { WebsiteCard } from "@/components/knowledge-hub/website-card";

export function WebsitesTab() {
  const websites = useKnowledgeHubStore((s) => s.websites);

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {websites.map((site) => (
        <WebsiteCard key={site.id} website={site} />
      ))}
    </div>
  );
}
