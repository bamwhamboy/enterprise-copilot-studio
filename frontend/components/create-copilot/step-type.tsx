"use client";

import { motion, AnimatePresence } from "framer-motion";

import { cn } from "@/lib/utils";
import { copilotTemplates } from "@/lib/copilot-templates";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface StepTypeProps {
  selectedTemplateId: string | null;
  onSelect: (templateId: string) => void;
  name: string;
  onNameChange: (value: string) => void;
  description: string;
  onDescriptionChange: (value: string) => void;
}

export function StepType({
  selectedTemplateId,
  onSelect,
  name,
  onNameChange,
  description,
  onDescriptionChange,
}: StepTypeProps) {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {copilotTemplates.map((template, index) => {
          const isSelected = template.id === selectedTemplateId;
          return (
            <motion.button
              key={template.id}
              type="button"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: index * 0.03 }}
              onClick={() => onSelect(template.id)}
              className={cn(
                "flex flex-col items-start gap-3 rounded-xl border p-4 text-left transition-all hover:-translate-y-0.5 hover:shadow-md",
                isSelected
                  ? "border-primary bg-primary/5 ring-2 ring-primary/20"
                  : "border-border bg-card"
              )}
            >
              <div
                className={cn(
                  "flex size-10 items-center justify-center rounded-xl bg-gradient-to-br",
                  template.accent
                )}
              >
                <template.icon className="size-5" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">{template.name}</p>
                <p className="mt-1 text-xs text-muted-foreground">{template.description}</p>
              </div>
            </motion.button>
          );
        })}
      </div>

      <AnimatePresence>
        {selectedTemplateId && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex flex-col gap-4 overflow-hidden rounded-xl border border-border bg-card p-4"
          >
            <div className="flex flex-col gap-2">
              <Label htmlFor="wizard-name">Copilot name</Label>
              <Input
                id="wizard-name"
                value={name}
                onChange={(e) => onNameChange(e.target.value)}
                placeholder="HR Assistant"
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="wizard-description">Description</Label>
              <Textarea
                id="wizard-description"
                value={description}
                onChange={(e) => onDescriptionChange(e.target.value)}
                rows={2}
                placeholder="What should this copilot help with?"
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
