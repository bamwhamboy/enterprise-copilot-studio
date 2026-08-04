"use client";

import { Search } from "lucide-react";

import { useKnowledgeHubStore } from "@/store/knowledge-hub-store";
import { Input } from "@/components/ui/input";

export function KnowledgeSearchBar() {
  const { searchQuery, setSearchQuery } = useKnowledgeHubStore();

  return (
    <div className="relative w-full sm:max-w-xs">
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        placeholder="Search documents..."
        className="h-9 bg-background pl-9"
      />
    </div>
  );
}
