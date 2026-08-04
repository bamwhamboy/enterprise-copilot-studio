import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface CreateCopilotBasicInfo {
  name: string;
  description: string;
  domain: string;
}

const DEFAULT_AI_COMPONENTS = [
  "retrieval-engine",
  "planner-agent",
  "conversation-memory",
  "tool-calling",
  "prompt-sanitization",
  "guardrails",
  "context-summarization",
  "semantic-cache",
  "llm-routing",
];

interface CreateCopilotState {
  currentStep: number; // 1-6
  basicInfo: CreateCopilotBasicInfo;
  knowledgeSourceIds: string[];
  aiComponentIds: string[];
  modelId: string;
  draftSavedAt: string | null;

  // Step 6 generation sequence (mock, client-only)
  generationStepIndex: number;
  isGenerationComplete: boolean;

  setName: (name: string) => void;
  setDescription: (description: string) => void;
  setDomain: (domain: string) => void;
  toggleKnowledgeSource: (id: string) => void;
  toggleAiComponent: (id: string) => void;
  setModel: (id: string) => void;

  goToStep: (step: number) => void;
  nextStep: () => void;
  prevStep: () => void;

  saveDraft: () => void;

  advanceGeneration: () => void;
  completeGeneration: () => void;
  resetGeneration: () => void;

  resetWizard: () => void;
}

const initialBasicInfo: CreateCopilotBasicInfo = {
  name: "",
  description: "",
  domain: "hr",
};

export const TOTAL_STEPS = 6;

export const useCreateCopilotStore = create<CreateCopilotState>()(
  persist(
    (set) => ({
      currentStep: 1,
      basicInfo: initialBasicInfo,
      knowledgeSourceIds: [],
      aiComponentIds: DEFAULT_AI_COMPONENTS,
      modelId: "groq-llama-3",
      draftSavedAt: null,

      generationStepIndex: 0,
      isGenerationComplete: false,

      setName: (name) =>
        set((state) => ({ basicInfo: { ...state.basicInfo, name } })),
      setDescription: (description) =>
        set((state) => ({ basicInfo: { ...state.basicInfo, description } })),
      setDomain: (domain) =>
        set((state) => ({ basicInfo: { ...state.basicInfo, domain } })),

      toggleKnowledgeSource: (id) =>
        set((state) => ({
          knowledgeSourceIds: state.knowledgeSourceIds.includes(id)
            ? state.knowledgeSourceIds.filter((s) => s !== id)
            : [...state.knowledgeSourceIds, id],
        })),

      toggleAiComponent: (id) =>
        set((state) => ({
          aiComponentIds: state.aiComponentIds.includes(id)
            ? state.aiComponentIds.filter((c) => c !== id)
            : [...state.aiComponentIds, id],
        })),

      setModel: (id) => set({ modelId: id }),

      goToStep: (step) =>
        set({ currentStep: Math.min(Math.max(step, 1), TOTAL_STEPS) }),
      nextStep: () =>
        set((state) => ({
          currentStep: Math.min(state.currentStep + 1, TOTAL_STEPS),
        })),
      prevStep: () =>
        set((state) => ({ currentStep: Math.max(state.currentStep - 1, 1) })),

      saveDraft: () => set({ draftSavedAt: new Date().toISOString() }),

      advanceGeneration: () =>
        set((state) => ({
          generationStepIndex: state.generationStepIndex + 1,
        })),
      completeGeneration: () => set({ isGenerationComplete: true }),
      resetGeneration: () =>
        set({ generationStepIndex: 0, isGenerationComplete: false }),

      resetWizard: () =>
        set({
          currentStep: 1,
          basicInfo: initialBasicInfo,
          knowledgeSourceIds: [],
          aiComponentIds: DEFAULT_AI_COMPONENTS,
          modelId: "groq-llama-3",
          generationStepIndex: 0,
          isGenerationComplete: false,
        }),
    }),
    {
      name: "ecs-create-copilot-draft",
      partialize: (state) => ({
        basicInfo: state.basicInfo,
        knowledgeSourceIds: state.knowledgeSourceIds,
        aiComponentIds: state.aiComponentIds,
        modelId: state.modelId,
        draftSavedAt: state.draftSavedAt,
      }),
    }
  )
);
