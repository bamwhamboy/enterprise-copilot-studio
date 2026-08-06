"use client";

import {
  ShieldCheck,
  KeyRound,
  Quote,
  Brain,
  UserCheck,
  Search,
  ClipboardList,
  Lock,
  Check,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";

const CAPABILITIES = [
  {
    id: "guardrails",
    label: "Guardrails",
    description: "Blocks prompt injection, jailbreaks, and unsafe output.",
    icon: ShieldCheck,
    enabled: true,
  },
  {
    id: "authentication",
    label: "Authentication",
    description: "JWT-authenticated access, scoped to your organization.",
    icon: KeyRound,
    enabled: true,
  },
  {
    id: "citations",
    label: "Citations",
    description: "Every answer links back to the source document.",
    icon: Quote,
    enabled: true,
  },
  {
    id: "memory",
    label: "Conversation Memory",
    description: "Remembers earlier turns within a session.",
    icon: Brain,
    enabled: true,
  },
  {
    id: "semantic-search",
    label: "Semantic Search",
    description: "Hybrid semantic + keyword retrieval over your documents.",
    icon: Search,
    enabled: true,
  },
  {
    id: "pii-protection",
    label: "PII Protection",
    description: "Automatically masks sensitive data in responses.",
    icon: Lock,
    enabled: true,
  },
  {
    id: "human-approval",
    label: "Human Approval",
    description: "Route sensitive actions through a human reviewer.",
    icon: UserCheck,
    enabled: false,
  },
  {
    id: "audit-logging",
    label: "Audit Logging",
    description: "Full audit trail of every conversation and action.",
    icon: ClipboardList,
    enabled: false,
  },
];

interface StepCapabilitiesProps {
  selectedIds: string[];
  onToggle: (id: string) => void;
}

export function StepCapabilities({ selectedIds, onToggle }: StepCapabilitiesProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {CAPABILITIES.map((capability) => {
        const isSelected = capability.enabled && selectedIds.includes(capability.id);
        return (
          <label
            key={capability.id}
            className={cn(
              "flex items-start gap-3 rounded-xl border p-3.5 transition-colors",
              capability.enabled
                ? cn("cursor-pointer", isSelected ? "border-primary/40 bg-primary/5" : "border-border hover:bg-accent/40")
                : "cursor-not-allowed border-border bg-muted/30 opacity-60"
            )}
          >
            {capability.enabled ? (
              <Checkbox
                checked={isSelected}
                onCheckedChange={() => onToggle(capability.id)}
                className="mt-0.5"
              />
            ) : (
              <div className="mt-0.5 flex size-4 items-center justify-center">
                <capability.icon className="size-4 text-muted-foreground" />
              </div>
            )}
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-foreground">{capability.label}</span>
                {capability.enabled ? (
                  isSelected && (
                    <Badge variant="success" className="gap-1 text-[10px]">
                      <Check className="size-2.5" />
                      On
                    </Badge>
                  )
                ) : (
                  <Badge variant="secondary" className="text-[10px]">
                    Coming Soon
                  </Badge>
                )}
              </div>
              <p className="mt-0.5 text-xs text-muted-foreground">{capability.description}</p>
            </div>
          </label>
        );
      })}
    </div>
  );
}
