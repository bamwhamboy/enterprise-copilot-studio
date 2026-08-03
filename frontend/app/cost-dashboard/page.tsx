import { Wallet } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function CostDashboardPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Cost Dashboard"
        description="Track spend across copilots, models, and teams."
        icon={Wallet}
      />
      <ComingSoon icon={Wallet} />
    </div>
  );
}
