import { CheckCircle2, Clock, Loader2, XCircle, FileQuestion } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { DocumentIndexStatus, DocumentProcessingStatus } from "@/types/knowledge-source";

export function ProcessingStatusBadge({ status }: { status: DocumentProcessingStatus | null }) {
  switch (status) {
    case "READY":
      return (
        <Badge variant="success" className="gap-1">
          <CheckCircle2 className="size-3" />
          Uploaded
        </Badge>
      );
    case "PROCESSING":
    case "UPLOADED":
      return (
        <Badge variant="warning" className="gap-1">
          <Loader2 className="size-3 animate-spin" />
          Processing
        </Badge>
      );
    case "FAILED":
      return (
        <Badge variant="destructive" className="gap-1">
          <XCircle className="size-3" />
          Failed
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="gap-1">
          <FileQuestion className="size-3" />
          Unknown
        </Badge>
      );
  }
}

export function IndexStatusBadge({ status }: { status: DocumentIndexStatus | null }) {
  switch (status) {
    case "INDEXED":
      return (
        <Badge variant="success" className="gap-1">
          <CheckCircle2 className="size-3" />
          Indexed
        </Badge>
      );
    case "INDEXING":
      return (
        <Badge variant="warning" className="gap-1">
          <Loader2 className="size-3 animate-spin" />
          Indexing
        </Badge>
      );
    case "FAILED":
      return (
        <Badge variant="destructive" className="gap-1">
          <XCircle className="size-3" />
          Failed
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="gap-1">
          <Clock className="size-3" />
          Not indexed
        </Badge>
      );
  }
}
