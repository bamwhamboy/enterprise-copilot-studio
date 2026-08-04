import { Upload, Database, Globe, FolderPlus } from "lucide-react";

import { Button } from "@/components/ui/button";

export function KnowledgeHubActions() {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button variant="outline" size="sm">
        <FolderPlus className="size-4" />
        Create Collection
      </Button>
      <Button variant="outline" size="sm">
        <Globe className="size-4" />
        Add Website
      </Button>
      <Button variant="outline" size="sm">
        <Database className="size-4" />
        Connect Database
      </Button>
      <Button size="sm">
        <Upload className="size-4" />
        Upload Documents
      </Button>
    </div>
  );
}
