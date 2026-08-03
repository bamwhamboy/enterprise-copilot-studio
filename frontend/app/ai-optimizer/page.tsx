import { Gauge } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function AiOptimizerPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="AI Optimizer"
        description="Tune latency, quality, and routing across models."
        icon={Gauge}
      />
      <ComingSoon icon={Gauge} />
    </div>
  );
}
