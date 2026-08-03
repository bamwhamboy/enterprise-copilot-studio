import { Settings } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function SettingsPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Settings"
        description="Workspace, security, and integration settings."
        icon={Settings}
      />
      <ComingSoon icon={Settings} />
    </div>
  );
}
