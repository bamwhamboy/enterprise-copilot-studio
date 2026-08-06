import { FileText, Hash } from "lucide-react";

import type { Citation } from "@/types/chat";

export function CitationCard({ citation, index }: { citation: Citation; index: number }) {
  return (
    <div className="flex items-start gap-2.5 rounded-lg border border-border bg-card px-3 py-2.5 transition-colors hover:border-primary/30 hover:bg-accent/40">
      <div className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/10 text-[11px] font-semibold text-primary">
        {index + 1}
      </div>
      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-1.5 truncate text-xs font-medium text-foreground">
          <FileText className="size-3 shrink-0 text-muted-foreground" />
          {citation.document_name}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
          {citation.section && <span>{citation.section}</span>}
          {citation.page_number !== null && <span>Page {citation.page_number}</span>}
          <span className="flex items-center gap-1">
            <Hash className="size-2.5" />
            Chunk {citation.chunk_number}
          </span>
        </div>
      </div>
    </div>
  );
}
