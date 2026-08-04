"use client";

import { FolderKanban } from "lucide-react";

import { cn } from "@/lib/utils";
import { useKnowledgeHubStore } from "@/store/knowledge-hub-store";
import type { CollectionStatus } from "@/types/knowledge-hub";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const statusConfig: Record<CollectionStatus, { label: string; dot: string; text: string }> = {
  active: { label: "Active", dot: "bg-success", text: "text-success" },
  syncing: { label: "Syncing", dot: "bg-primary animate-pulse", text: "text-primary" },
  attention: { label: "Needs Attention", dot: "bg-warning", text: "text-warning" },
};

export function CollectionsPanel() {
  const { collections, selectedCollectionId, setSelectedCollection } =
    useKnowledgeHubStore();

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm">Collections</CardTitle>
        <FolderKanban className="size-4 text-muted-foreground" />
      </CardHeader>
      <CardContent className="flex flex-col gap-1.5">
        {collections.map((collection) => {
          const status = statusConfig[collection.status];
          const isSelected = selectedCollectionId === collection.id;

          return (
            <button
              key={collection.id}
              type="button"
              onClick={() => setSelectedCollection(collection.id)}
              className={cn(
                "flex flex-col gap-1 rounded-lg border border-transparent px-3 py-2.5 text-left transition-colors",
                "hover:bg-accent hover:text-accent-foreground",
                isSelected && "border-primary/30 bg-primary/5"
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-foreground">
                  {collection.name}
                </span>
                <span className={cn("flex size-1.5 shrink-0 rounded-full", status.dot)} />
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{collection.documentCount} documents</span>
                <span>{collection.lastUpdated}</span>
              </div>
            </button>
          );
        })}

        {selectedCollectionId && (
          <button
            type="button"
            onClick={() => setSelectedCollection(null)}
            className="mt-1 rounded-lg px-3 py-1.5 text-left text-xs font-medium text-primary hover:underline"
          >
            Clear filter
          </button>
        )}
      </CardContent>
    </Card>
  );
}
