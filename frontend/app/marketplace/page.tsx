import { Store } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function MarketplacePage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Copilot Marketplace"
        description="Discover and deploy ready-made copilot templates."
        icon={Store}
      />
      <ComingSoon icon={Store} />
    </div>
  );
}
