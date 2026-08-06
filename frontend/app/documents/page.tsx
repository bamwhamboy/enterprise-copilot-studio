"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileStack, Search, ChevronLeft, ChevronRight } from "lucide-react";

import { documentsApi } from "@/lib/api/documents";
import { knowledgeSourcesApi } from "@/lib/api/knowledge-sources";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  ProcessingStatusBadge,
  IndexStatusBadge,
} from "@/components/shared/document-status-badges";

const PAGE_SIZE = 10;

export default function DocumentsPage() {
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [page, setPage] = useState(0);

  const { data: sources } = useQuery({
    queryKey: ["knowledge-sources"],
    queryFn: knowledgeSourcesApi.list,
  });

  const { data: documents, isLoading } = useQuery({
    queryKey: ["documents", sourceFilter, page],
    queryFn: () =>
      documentsApi.list({
        knowledge_source_id: sourceFilter === "all" ? undefined : sourceFilter,
        offset: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
  });

  const sourceNameById = useMemo(() => {
    const map = new Map<string, string>();
    sources?.forEach((s) => map.set(s.id, s.name));
    return map;
  }, [sources]);

  const filteredDocuments = useMemo(() => {
    if (!documents) return [];
    if (!search.trim()) return documents;
    const query = search.toLowerCase();
    return documents.filter((doc) =>
      (doc.original_filename || doc.name).toLowerCase().includes(query)
    );
  }, [documents, search]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Documents"
        description="Every document uploaded across your knowledge sources."
        icon={FileStack}
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search documents on this page…"
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          value={sourceFilter}
          onChange={(e) => {
            setSourceFilter(e.target.value);
            setPage(0);
          }}
          className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30 sm:w-56"
        >
          <option value="all">All knowledge sources</option>
          {sources?.map((source) => (
            <option key={source.id} value={source.id}>
              {source.name}
            </option>
          ))}
        </select>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex flex-col gap-3 p-4">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full rounded-md" />
              ))}
            </div>
          ) : filteredDocuments.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
              <p className="text-sm font-medium text-foreground">No documents found</p>
              <p className="text-xs text-muted-foreground">
                Try a different search term, filter, or upload a document from Knowledge Sources.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-muted-foreground">
                    <th className="px-4 py-3 font-medium">Name</th>
                    <th className="px-4 py-3 font-medium">Knowledge Source</th>
                    <th className="px-4 py-3 font-medium">Pages</th>
                    <th className="px-4 py-3 font-medium">Chunks</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Index</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredDocuments.map((doc) => (
                    <tr key={doc.id} className="transition-colors hover:bg-accent/40">
                      <td className="max-w-xs truncate px-4 py-3 font-medium text-foreground">
                        {doc.original_filename || doc.name}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {sourceNameById.get(doc.knowledge_source_id) ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{doc.pages}</td>
                      <td className="px-4 py-3 text-muted-foreground">{doc.chunks}</td>
                      <td className="px-4 py-3">
                        <ProcessingStatusBadge status={doc.processing_status} />
                      </td>
                      <td className="px-4 py-3">
                        <IndexStatusBadge status={doc.index_status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Page {page + 1} · {documents?.length ?? 0} document{documents?.length !== 1 ? "s" : ""} on this page
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
          >
            <ChevronLeft className="size-3.5" />
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={!documents || documents.length < PAGE_SIZE}
          >
            Next
            <ChevronRight className="size-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
