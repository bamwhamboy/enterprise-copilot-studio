"use client";

import { useKnowledgeHubStore } from "@/store/knowledge-hub-store";
import { DatabaseCard } from "@/components/knowledge-hub/database-card";

export function DatabasesTab() {
  const databases = useKnowledgeHubStore((s) => s.databases);

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {databases.map((db) => (
        <DatabaseCard key={db.id} database={db} />
      ))}
    </div>
  );
}
