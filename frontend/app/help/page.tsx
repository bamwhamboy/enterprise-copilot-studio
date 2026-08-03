import { HelpCircle } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function HelpPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Help"
        description="Documentation, guides, and support resources."
        icon={HelpCircle}
      />
      <ComingSoon icon={HelpCircle} />
    </div>
  );
}
