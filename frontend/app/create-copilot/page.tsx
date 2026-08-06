"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, Sparkles, AlertCircle, X } from "lucide-react";

import { copilotsApi } from "@/lib/api/copilots";
import { knowledgeSourcesApi } from "@/lib/api/knowledge-sources";
import { copilotTemplates } from "@/lib/copilot-templates";
import type { Copilot } from "@/types/copilot";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { WizardStepper } from "@/components/create-copilot/wizard-stepper";
import { StepType } from "@/components/create-copilot/step-type";
import { StepKnowledgeSources } from "@/components/create-copilot/step-knowledge-sources";
import { StepModel } from "@/components/create-copilot/step-model";
import { StepCapabilities } from "@/components/create-copilot/step-capabilities";
import { StepReview } from "@/components/create-copilot/step-review";
import { SequenceLoader, type SequenceStepDef } from "@/components/shared/sequence-loader";
import { LaunchCopilotButton } from "@/components/shared/launch-copilot-button";

const MODEL = "llama-3.3-70b-versatile";
const CREATION_STEPS: SequenceStepDef[] = [
  { id: "create", label: "Creating Copilot" },
  { id: "metadata", label: "Registering Metadata" },
  { id: "retrieval", label: "Initializing Retrieval" },
  { id: "linking", label: "Linking Knowledge Sources" },
  { id: "agent", label: "Preparing AI Agent" },
  { id: "ready", label: "Ready" },
];

export default function CreateCopilotWizardPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const initialTemplate = (() => {
    const requested = searchParams.get("template");
    return copilotTemplates.find((t) => t.id === requested) ?? null;
  })();

  const [step, setStep] = useState(1);
  const [templateId, setTemplateId] = useState<string | null>(initialTemplate?.id ?? null);
  const [name, setName] = useState(initialTemplate?.name ?? "");
  const [description, setDescription] = useState(initialTemplate?.description ?? "");
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);
  const [selectedCapabilities, setSelectedCapabilities] = useState<string[]>([
    "guardrails",
    "authentication",
    "citations",
    "memory",
    "semantic-search",
    "pii-protection",
  ]);
  const [isCreating, setIsCreating] = useState(false);
  const [animationDone, setAnimationDone] = useState(false);
  const [createdCopilot, setCreatedCopilot] = useState<Copilot | null>(null);

  const { data: knowledgeSources } = useQuery({
    queryKey: ["knowledge-sources"],
    queryFn: knowledgeSourcesApi.list,
  });

  const createMutation = useMutation({
    mutationFn: () => {
      const template = copilotTemplates.find((t) => t.id === templateId);
      return copilotsApi.create({
        name: name || template?.name || "New Copilot",
        description: description || undefined,
        domain: template?.domain ?? "hr",
        status: "active",
        model: MODEL,
        knowledge_source_ids: selectedSourceIds,
      });
    },
    onSuccess: (copilot) => {
      queryClient.invalidateQueries({ queryKey: ["copilots"] });
      setCreatedCopilot(copilot);
    },
  });

  function selectTemplate(id: string) {
    setTemplateId(id);
    const template = copilotTemplates.find((t) => t.id === id);
    if (template) {
      setName(template.name);
      setDescription(template.description);
    }
  }

  function toggleSource(id: string) {
    setSelectedSourceIds((prev) =>
      prev.includes(id) ? prev.filter((sid) => sid !== id) : [...prev, id]
    );
  }

  function toggleCapability(id: string) {
    setSelectedCapabilities((prev) =>
      prev.includes(id) ? prev.filter((cid) => cid !== id) : [...prev, id]
    );
  }

  const canProceed = step === 1 ? Boolean(templateId && name.trim()) : true;

  function handleNext() {
    if (step === 5) {
      setIsCreating(true);
      createMutation.mutate();
      return;
    }
    setStep((s) => Math.min(5, s + 1));
  }

  if (isCreating) {
    if (createMutation.isError) {
      return (
        <div className="mx-auto flex max-w-lg flex-col items-center gap-4 py-16 text-center">
          <div className="flex size-14 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
            <AlertCircle className="size-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">Couldn&apos;t create this copilot</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {(createMutation.error as { message?: string })?.message ??
                "Something went wrong. Please try again."}
            </p>
          </div>
          <Button
            variant="outline"
            onClick={() => {
              setIsCreating(false);
              setAnimationDone(false);
              createMutation.reset();
            }}
          >
            Back to review
          </Button>
        </div>
      );
    }

    // Animation finished and the copilot genuinely exists on the backend
    // -- let the user choose what happens next, rather than launching
    // straight into chat automatically.
    if (animationDone && createdCopilot) {
      return (
        <div className="mx-auto flex max-w-md flex-col items-center gap-5 py-16 text-center">
          <motion.div
            initial={{ scale: 0.7, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            className="flex size-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-[#5b7cfa] text-3xl shadow-lg shadow-primary/25"
          >
            🎉
          </motion.div>
          <div>
            <p className="text-lg font-semibold text-foreground">
              Copilot Created Successfully
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              &quot;{createdCopilot.name}&quot; is ready whenever you are.
            </p>
          </div>
          <div className="flex w-full flex-col gap-2 sm:flex-row">
            <Button variant="outline" className="flex-1" onClick={() => router.push("/")}>
              Return to Dashboard
            </Button>
            <LaunchCopilotButton
              copilotId={createdCopilot.id}
              copilotName={createdCopilot.name}
              size="default"
              className="flex-1"
            />
          </div>
        </div>
      );
    }

    return (
      <Card className="mx-auto max-w-md">
        <CardContent>
          <SequenceLoader
            title="Creating your copilot"
            icon={Sparkles}
            steps={CREATION_STEPS}
            onComplete={() => setAnimationDone(true)}
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <PageHeader
        title="Create Copilot"
        description="Set up a new enterprise copilot in a few guided steps."
        icon={Sparkles}
        actions={
          <Button variant="ghost" size="icon" onClick={() => router.push("/copilots")}>
            <X className="size-4" />
          </Button>
        }
      />

      <WizardStepper currentStep={step} />

      <Card>
        <CardContent className="pt-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -12 }}
              transition={{ duration: 0.2 }}
            >
              {step === 1 && (
                <StepType
                  selectedTemplateId={templateId}
                  onSelect={selectTemplate}
                  name={name}
                  onNameChange={setName}
                  description={description}
                  onDescriptionChange={setDescription}
                />
              )}
              {step === 2 && (
                <StepKnowledgeSources
                  knowledgeSources={knowledgeSources ?? []}
                  selectedIds={selectedSourceIds}
                  onToggle={toggleSource}
                />
              )}
              {step === 3 && <StepModel selectedModel={MODEL} />}
              {step === 4 && (
                <StepCapabilities selectedIds={selectedCapabilities} onToggle={toggleCapability} />
              )}
              {step === 5 && (
                <StepReview
                  templateId={templateId}
                  name={name}
                  description={description}
                  knowledgeSources={knowledgeSources ?? []}
                  selectedSourceIds={selectedSourceIds}
                  model={MODEL}
                  capabilities={selectedCapabilities}
                />
              )}
            </motion.div>
          </AnimatePresence>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={() => setStep((s) => Math.max(1, s - 1))}
          disabled={step === 1}
        >
          <ChevronLeft className="size-4" />
          Back
        </Button>
        <Button onClick={handleNext} disabled={!canProceed}>
          {step === 5 ? "Create Copilot" : "Continue"}
          {step < 5 && <ChevronRight className="size-4" />}
        </Button>
      </div>
    </div>
  );
}
