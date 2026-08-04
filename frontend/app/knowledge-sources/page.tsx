import { Database } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function KnowledgeSourcesPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Knowledge Sources"
        description="Manage documents and connectors that power retrieval."
        icon={Database}
      />
      <ComingSoon icon={Database} />
    </div>
  );
}
