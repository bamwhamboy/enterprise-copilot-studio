"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

import type { ApiKnowledgeSource, KnowledgeSourceCreatePayload } from "@/types/knowledge-source";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const SOURCE_TYPES: { value: ApiKnowledgeSource["source_type"]; label: string; enabled: boolean }[] = [
  { value: "documents", label: "Documents (PDF upload)", enabled: true },
  { value: "database", label: "Database — coming soon", enabled: false },
  { value: "website", label: "Website — coming soon", enabled: false },
  { value: "connector", label: "Connector — coming soon", enabled: false },
];

interface CreateSourceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: KnowledgeSourceCreatePayload) => void;
  isSubmitting: boolean;
}

export function CreateSourceDialog({
  open,
  onOpenChange,
  onSubmit,
  isSubmitting,
}: CreateSourceDialogProps) {
  const [name, setName] = useState("");
  const [sourceType, setSourceType] = useState<ApiKnowledgeSource["source_type"]>("documents");

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    onSubmit({ name, source_type: sourceType });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Knowledge Source</DialogTitle>
          <DialogDescription>
            A knowledge source groups documents that get chunked, embedded, and made
            searchable for your copilots.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="source-name">Name</Label>
            <Input
              id="source-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="HR Policies"
              required
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="source-type">Type</Label>
            <select
              id="source-type"
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value as ApiKnowledgeSource["source_type"])}
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30"
            >
              {SOURCE_TYPES.map((type) => (
                <option key={type.value} value={type.value} disabled={!type.enabled}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || !name.trim()}>
              {isSubmitting && <Loader2 className="size-4 animate-spin" />}
              Create
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
