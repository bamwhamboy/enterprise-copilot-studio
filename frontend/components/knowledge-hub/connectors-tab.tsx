import {
  Share2,
  BookOpen,
  FolderOpen,
  Cloud,
  Building2,
  Server,
  Users,
  Calendar,
  LifeBuoy,
} from "lucide-react";

import type { EnterpriseConnector } from "@/types/knowledge-hub";
import { Badge } from "@/components/ui/badge";

const connectors: EnterpriseConnector[] = [
  { id: "sharepoint", name: "SharePoint", icon: Share2 },
  { id: "confluence", name: "Confluence", icon: BookOpen },
  { id: "google-drive", name: "Google Drive", icon: FolderOpen },
  { id: "onedrive", name: "OneDrive", icon: Cloud },
  { id: "salesforce", name: "Salesforce", icon: Building2 },
  { id: "sap", name: "SAP", icon: Server },
  { id: "successfactors", name: "SuccessFactors", icon: Users },
  { id: "workday", name: "Workday", icon: Calendar },
  { id: "servicenow", name: "ServiceNow", icon: LifeBuoy },
];

export function ConnectorsTab() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
      {connectors.map((connector) => (
        <div
          key={connector.id}
          className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border bg-muted/30 px-3 py-5 text-center opacity-80"
        >
          <div className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground grayscale">
            <connector.icon className="size-4" />
          </div>
          <span className="text-xs font-medium text-foreground">
            {connector.name}
          </span>
          <Badge variant="secondary">Coming Soon</Badge>
        </div>
      ))}
    </div>
  );
}
