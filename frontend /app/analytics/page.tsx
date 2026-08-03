import { BarChart3 } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function AnalyticsPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Analytics"
        description="Usage, adoption, and quality metrics across the platform."
        icon={BarChart3}
      />
      <ComingSoon icon={BarChart3} />
    </div>
  );
}
