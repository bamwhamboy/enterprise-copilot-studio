"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

import type { ApiKnowledgeSource } from "@/types/knowledge-source";
import type { Copilot, CopilotCreatePayload, CopilotDomain } from "@/types/copilot";
import { COPILOT_DOMAIN_LABELS } from "@/types/copilot";
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
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";

interface CopilotFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  copilot?: Copilot;
  knowledgeSources: ApiKnowledgeSource[];
  onSubmit: (payload: CopilotCreatePayload) => void;
  isSubmitting: boolean;
}

const DOMAINS = Object.keys(COPILOT_DOMAIN_LABELS) as CopilotDomain[];

/**
 * Initializes its local form state directly from `copilot` (a prop, not
 * an effect syncing state to a prop change) -- the parent remounts this
 * component with a fresh `key` whenever it should reset (switching
 * between "create" and "edit", or between two different copilots), so
 * there's no stale-state case to handle here. This is the pattern
 * React's own docs recommend over useEffect-based state resets.
 */
export function CopilotFormDialog({
  open,
  onOpenChange,
  copilot,
  knowledgeSources,
  onSubmit,
  isSubmitting,
}: CopilotFormDialogProps) {
  const isEdit = Boolean(copilot);
  const [name, setName] = useState(copilot?.name ?? "");
  const [description, setDescription] = useState(copilot?.description ?? "");
  const [domain, setDomain] = useState<CopilotDomain>(copilot?.domain ?? "hr");
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>(
    copilot?.knowledge_sources.map((k) => k.id) ?? []
  );

  function toggleSource(id: string) {
    setSelectedSourceIds((prev) =>
      prev.includes(id) ? prev.filter((sid) => sid !== id) : [...prev, id]
    );
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    onSubmit({
      name,
      description: description || undefined,
      domain,
      knowledge_source_ids: selectedSourceIds,
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit Copilot" : "Create Copilot"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Update this copilot's details and linked knowledge sources."
              : "Set up a new enterprise copilot grounded in your knowledge sources."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="copilot-name">Name</Label>
            <Input
              id="copilot-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="HR Copilot"
              required
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="copilot-description">Description</Label>
            <Textarea
              id="copilot-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Answers employee questions grounded in HR policy documents."
              rows={3}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="copilot-domain">Domain</Label>
            <select
              id="copilot-domain"
              value={domain}
              onChange={(e) => setDomain(e.target.value as CopilotDomain)}
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30"
            >
              {DOMAINS.map((d) => (
                <option key={d} value={d}>
                  {COPILOT_DOMAIN_LABELS[d]}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-2">
            <Label>Knowledge sources</Label>
            {knowledgeSources.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No knowledge sources yet — create one first to ground this copilot.
              </p>
            ) : (
              <div className="flex max-h-40 flex-col gap-2 overflow-y-auto rounded-lg border border-border p-3">
                {knowledgeSources.map((source) => (
                  <label
                    key={source.id}
                    className="flex cursor-pointer items-center gap-2 text-sm text-foreground"
                  >
                    <Checkbox
                      checked={selectedSourceIds.includes(source.id)}
                      onCheckedChange={() => toggleSource(source.id)}
                    />
                    {source.name}
                  </label>
                ))}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || !name.trim()}>
              {isSubmitting && <Loader2 className="size-4 animate-spin" />}
              {isEdit ? "Save changes" : "Create Copilot"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
