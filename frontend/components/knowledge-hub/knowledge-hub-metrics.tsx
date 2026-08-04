import { FileText, FolderKanban, Layers, LayoutGrid, Atom, Clock } from "lucide-react";

import type { StatCardData } from "@/types/dashboard";
import { StatCard } from "@/components/dashboard/stat-card";

const metrics: StatCardData[] = [
  { id: "documents", label: "Documents", value: "148", icon: FileText },
  { id: "collections", label: "Collections", value: "12", icon: FolderKanban },
  { id: "sources", label: "Knowledge Sources", value: "26", icon: Layers },
  { id: "chunks", label: "Indexed Chunks", value: "42,381", icon: LayoutGrid },
  { id: "embeddings", label: "Embeddings", value: "42,381", icon: Atom },
  { id: "last-indexed", label: "Last Indexed", value: "5 min ago", icon: Clock },
];

export function KnowledgeHubMetrics() {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6">
      {metrics.map((metric) => (
        <StatCard key={metric.id} data={metric} />
      ))}
    </div>
  );
}
