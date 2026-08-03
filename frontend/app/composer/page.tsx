import { Wand2 } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function ComposerPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Copilot Composer"
        description="Compose new copilots from reusable AI components."
        icon={Wand2}
      />
      <ComingSoon icon={Wand2} />
    </div>
  );
}
