import { create } from "zustand";

import type {
  KnowledgeHubTab,
  KnowledgeCollection,
  KnowledgeDocument,
  KnowledgeDatabase,
  KnowledgeWebsite,
} from "@/types/knowledge-hub";

const initialCollections: KnowledgeCollection[] = [
  { id: "hr-policies", name: "HR Policies", documentCount: 8, status: "active", lastUpdated: "5 min ago" },
  { id: "finance", name: "Finance", documentCount: 4, status: "active", lastUpdated: "2 hr ago" },
  { id: "it-support", name: "IT Support", documentCount: 6, status: "syncing", lastUpdated: "12 min ago" },
  { id: "legal", name: "Legal", documentCount: 3, status: "active", lastUpdated: "1 day ago" },
  { id: "engineering", name: "Engineering", documentCount: 3, status: "attention", lastUpdated: "3 days ago" },
  { id: "operations", name: "Operations", documentCount: 2, status: "active", lastUpdated: "6 hr ago" },
];

const initialDocuments: KnowledgeDocument[] = [
  { id: "d1", name: "Employee Handbook.pdf", collectionId: "hr-policies", status: "indexed", pages: 28, chunks: 182, embeddings: 182, uploadedAt: "Yesterday" },
  { id: "d2", name: "Leave Policy.pdf", collectionId: "hr-policies", status: "indexed", pages: 6, chunks: 41, embeddings: 41, uploadedAt: "3 days ago" },
  { id: "d3", name: "Benefits Guide.pdf", collectionId: "hr-policies", status: "indexed", pages: 14, chunks: 96, embeddings: 96, uploadedAt: "1 week ago" },
  { id: "d4", name: "Travel Policy.pdf", collectionId: "finance", status: "indexed", pages: 9, chunks: 58, embeddings: 58, uploadedAt: "1 week ago" },
  { id: "d5", name: "Code of Conduct.pdf", collectionId: "legal", status: "indexed", pages: 12, chunks: 74, embeddings: 74, uploadedAt: "2 weeks ago" },
  { id: "d6", name: "Medical Insurance.pdf", collectionId: "hr-policies", status: "processing", pages: 18, chunks: 0, embeddings: 0, uploadedAt: "2 hr ago" },
  { id: "d7", name: "Learning & Development.pdf", collectionId: "engineering", status: "indexed", pages: 22, chunks: 133, embeddings: 133, uploadedAt: "1 month ago" },
  { id: "d8", name: "Remote Work Policy.pdf", collectionId: "operations", status: "indexed", pages: 7, chunks: 45, embeddings: 45, uploadedAt: "1 month ago" },
  { id: "d9", name: "Employee FAQ.pdf", collectionId: "hr-policies", status: "pending", pages: 15, chunks: 0, embeddings: 0, uploadedAt: "10 min ago" },
];

const initialDatabases: KnowledgeDatabase[] = [
  { id: "hr-postgresql", name: "HR PostgreSQL", engine: "PostgreSQL", description: "Core employee and org records.", status: "connected" },
  { id: "oracle-hr", name: "Oracle HR", engine: "Oracle", description: "Legacy payroll and compensation data.", status: "connected" },
  { id: "snowflake-hr", name: "Snowflake HR", engine: "Snowflake", description: "Analytics warehouse for HR reporting.", status: "coming-soon" },
  { id: "workday-db", name: "Workday", engine: "Workday", description: "Benefits, leave, and performance data.", status: "coming-soon" },
];

const initialWebsites: KnowledgeWebsite[] = [
  { id: "company-portal", name: "Company Portal", url: "portal.enterprise.internal", status: "indexed", lastCrawled: "3 hr ago" },
  { id: "employee-wiki", name: "Employee Wiki", url: "wiki.enterprise.internal", status: "indexed", lastCrawled: "1 day ago" },
  { id: "benefits-portal", name: "Benefits Portal", url: "benefits.enterprise.internal", status: "pending", lastCrawled: "Never" },
];

interface KnowledgeHubState {
  activeTab: KnowledgeHubTab;
  selectedCollectionId: string | null;
  searchQuery: string;
  activeDocumentId: string | null;
  isDrawerOpen: boolean;

  collections: KnowledgeCollection[];
  documents: KnowledgeDocument[];
  databases: KnowledgeDatabase[];
  websites: KnowledgeWebsite[];

  setActiveTab: (tab: KnowledgeHubTab) => void;
  setSelectedCollection: (id: string | null) => void;
  setSearchQuery: (query: string) => void;

  openDocument: (id: string) => void;
  closeDrawer: () => void;

  deleteDocument: (id: string) => void;
  reindexDocument: (id: string) => void;
}

export const useKnowledgeHubStore = create<KnowledgeHubState>()((set, get) => ({
  activeTab: "documents",
  selectedCollectionId: null,
  searchQuery: "",
  activeDocumentId: null,
  isDrawerOpen: false,

  collections: initialCollections,
  documents: initialDocuments,
  databases: initialDatabases,
  websites: initialWebsites,

  setActiveTab: (tab) => set({ activeTab: tab }),
  setSelectedCollection: (id) =>
    set((state) => ({
      selectedCollectionId: state.selectedCollectionId === id ? null : id,
    })),
  setSearchQuery: (query) => set({ searchQuery: query }),

  openDocument: (id) => set({ activeDocumentId: id, isDrawerOpen: true }),
  closeDrawer: () => set({ isDrawerOpen: false }),

  deleteDocument: (id) =>
    set((state) => ({
      documents: state.documents.filter((doc) => doc.id !== id),
      isDrawerOpen: state.activeDocumentId === id ? false : state.isDrawerOpen,
    })),

  reindexDocument: (id) => {
    set((state) => ({
      documents: state.documents.map((doc) =>
        doc.id === id ? { ...doc, status: "processing" } : doc
      ),
    }));

    // Mock async re-index — purely client-side, no backend call.
    window.setTimeout(() => {
      const doc = get().documents.find((d) => d.id === id);
      if (!doc) return;
      set((state) => ({
        documents: state.documents.map((d) =>
          d.id === id
            ? {
                ...d,
                status: "indexed",
                chunks: d.chunks || Math.floor(Math.random() * 80) + 40,
                embeddings: d.embeddings || Math.floor(Math.random() * 80) + 40,
              }
            : d
        ),
      }));
    }, 1400);
  },
}));
