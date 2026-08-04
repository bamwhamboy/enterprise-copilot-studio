"use client";

import { AnimatePresence, motion } from "framer-motion";
import { FileSearch } from "lucide-react";

import { useKnowledgeHubStore } from "@/store/knowledge-hub-store";
import { DocumentCard } from "@/components/knowledge-hub/document-card";

export function DocumentsTab() {
  const { documents, collections, selectedCollectionId, searchQuery } =
    useKnowledgeHubStore();

  const filtered = documents.filter((doc) => {
    const matchesCollection =
      !selectedCollectionId || doc.collectionId === selectedCollectionId;
    const matchesSearch = doc.name
      .toLowerCase()
      .includes(searchQuery.trim().toLowerCase());
    return matchesCollection && matchesSearch;
  });

  const collectionName = collections.find(
    (c) => c.id === selectedCollectionId
  )?.name;

  if (filtered.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-muted/30 py-16 text-center">
        <FileSearch className="size-6 text-muted-foreground" />
        <p className="text-sm font-medium text-foreground">No documents found</p>
        <p className="max-w-xs text-xs text-muted-foreground">
          {searchQuery
            ? `No documents match "${searchQuery}".`
            : `No documents in ${collectionName ?? "this collection"} yet.`}
        </p>
      </div>
    );
  }

  return (
    <motion.div
      layout
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3"
    >
      <AnimatePresence initial={false}>
        {filtered.map((doc) => (
          <motion.div
            key={doc.id}
            layout
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.2 }}
          >
            <DocumentCard document={doc} />
          </motion.div>
        ))}
      </AnimatePresence>
    </motion.div>
  );
}
