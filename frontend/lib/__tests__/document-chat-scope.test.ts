import { describe, expect, it } from "vitest";

import { findSoleAttachedCopilot } from "@/lib/document-chat-scope";
import type { Copilot } from "@/types/copilot";

function makeCopilot(id: string, knowledgeSourceIds: string[]): Copilot {
  return {
    id,
    name: `Copilot ${id}`,
    description: null,
    domain: "hr",
    status: "active",
    model: "gpt-4",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    knowledge_sources: knowledgeSourceIds.map((ksId) => ({
      id: ksId,
      name: `KS ${ksId}`,
      source_type: "documents",
      status: "active",
    })),
  };
}

describe("findSoleAttachedCopilot", () => {
  it("d.1: returns the copilot when exactly one has this knowledge source attached", () => {
    const copilots = [makeCopilot("c1", ["ks-1"]), makeCopilot("c2", ["ks-2"])];
    expect(findSoleAttachedCopilot(copilots, "ks-1")?.id).toBe("c1");
  });

  it("d.2: returns undefined when zero copilots have this knowledge source attached", () => {
    const copilots = [makeCopilot("c1", ["ks-2"])];
    expect(findSoleAttachedCopilot(copilots, "ks-1")).toBeUndefined();
  });

  it("d.3: returns undefined when multiple copilots share this knowledge source -- never guesses", () => {
    const copilots = [makeCopilot("c1", ["ks-1"]), makeCopilot("c2", ["ks-1"])];
    expect(findSoleAttachedCopilot(copilots, "ks-1")).toBeUndefined();
  });

  it("d.4: returns undefined when the copilots list hasn't loaded yet", () => {
    expect(findSoleAttachedCopilot(undefined, "ks-1")).toBeUndefined();
  });

  it("d.5: a copilot with multiple knowledge sources still matches on the requested one", () => {
    const copilots = [makeCopilot("c1", ["ks-1", "ks-2", "ks-3"])];
    expect(findSoleAttachedCopilot(copilots, "ks-2")?.id).toBe("c1");
  });
});
