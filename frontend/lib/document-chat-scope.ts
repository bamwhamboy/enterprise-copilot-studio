import type { Copilot } from "@/types/copilot";

/**
 * Fix #2C: "Chat with this document" is only offered when it's
 * unambiguous which copilot to launch into -- i.e. exactly one of the
 * organization's copilots has this knowledge source attached. Zero or
 * multiple attached copilots return undefined rather than guessing.
 */
export function findSoleAttachedCopilot(
  copilots: Copilot[] | undefined,
  knowledgeSourceId: string
): Copilot | undefined {
  if (!copilots) return undefined;
  const attached = copilots.filter((copilot) =>
    copilot.knowledge_sources.some((ks) => ks.id === knowledgeSourceId)
  );
  return attached.length === 1 ? attached[0] : undefined;
}
