import { Blocks } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function AiComponentsPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="AI Components"
        description="Reusable retrieval, memory, and guardrail building blocks."
        icon={Blocks}
      />
      <ComingSoon icon={Blocks} />
    </div>
  );
}
