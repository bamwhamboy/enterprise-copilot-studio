"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Wand2, ChevronLeft, ChevronRight, Save, X, Check } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useCreateCopilotStore } from "@/app/create-copilot/store/create-copilot-store";
import { WizardStepper } from "@/app/create-copilot/components/wizard-stepper";
import { StepBasicInformation } from "@/app/create-copilot/components/step-basic-information";
import { StepKnowledgeSources } from "@/app/create-copilot/components/step-knowledge-sources";
import { StepAiComponents } from "@/app/create-copilot/components/step-ai-components";
import { StepModelSelection } from "@/app/create-copilot/components/step-model-selection";
import { StepReview } from "@/app/create-copilot/components/step-review";
import { StepSuccess } from "@/app/create-copilot/components/step-success";

export default function CreateCopilotPage() {
  const {
    currentStep,
    basicInfo,
    knowledgeSourceIds,
    nextStep,
    prevStep,
    saveDraft,
  } = useCreateCopilotStore();

  const [showSaved, setShowSaved] = useState(false);

  const handleSaveDraft = () => {
    saveDraft();
    setShowSaved(true);
    window.setTimeout(() => setShowSaved(false), 2000);
  };

  const canProceed =
    (currentStep === 1 && basicInfo.name.trim().length > 0) ||
    (currentStep === 2 && knowledgeSourceIds.length > 0) ||
    currentStep === 3 ||
    currentStep === 4 ||
    currentStep === 5;

  const isReviewStep = currentStep === 5;
  const isGenerateStep = currentStep === 6;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Create Copilot"
        description="Compose a new enterprise AI copilot from reusable AI components."
        icon={Wand2}
      />

      {!isGenerateStep && (
        <Card>
          <CardContent className="pt-6">
            <WizardStepper currentStep={currentStep} />
          </CardContent>
        </Card>
      )}

      <Card className="min-h-[420px]">
        <CardContent className="pt-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -12 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              {currentStep === 1 && <StepBasicInformation />}
              {currentStep === 2 && <StepKnowledgeSources />}
              {currentStep === 3 && <StepAiComponents />}
              {currentStep === 4 && <StepModelSelection />}
              {currentStep === 5 && <StepReview />}
              {currentStep === 6 && <StepSuccess />}
            </motion.div>
          </AnimatePresence>
        </CardContent>
      </Card>

      {!isGenerateStep && (
        <div className="flex flex-col-reverse items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost">
              <Link href="/">
                <X className="size-4" />
                Cancel
              </Link>
            </Button>
            <Button variant="outline" onClick={handleSaveDraft}>
              {showSaved ? <Check className="size-4" /> : <Save className="size-4" />}
              {showSaved ? "Saved" : "Save Draft"}
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={prevStep}
              disabled={currentStep === 1}
            >
              <ChevronLeft className="size-4" />
              Previous
            </Button>
            <Button onClick={nextStep} disabled={!canProceed}>
              {isReviewStep ? "Generate Copilot" : "Next"}
              {!isReviewStep && <ChevronRight className="size-4" />}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
