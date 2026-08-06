import type { LucideIcon } from "lucide-react";
import type { CopilotDomain } from "@/types/copilot";

/**
 * Preset starting points for the Create Copilot wizard's "Choose Copilot
 * Type" step, and the cards shown on /marketplace. These are templates
 * (name/description/icon/suggested domain) a user picks to prefill the
 * wizard -- not real backend entities, so they're never presented
 * alongside or mistaken for a user's actual copilots (which come from
 * the real API everywhere else in the app).
 */
export interface CopilotTemplate {
  id: string;
  name: string;
  description: string;
  domain: CopilotDomain;
  icon: LucideIcon;
  accent: string; // tailwind gradient stop classes, for visual variety
  /**
   * True for templates whose domain is a direct, exact match to the
   * backend's domain enum. Templates whose domain had to be approximated
   * (e.g. "Clinical Research Assistant" -> "analytics", the closest real
   * bucket) are marked unavailable and shown in a separate "Coming Soon"
   * section on the Marketplace, rather than presented with the same
   * confidence as an exact match.
   */
  available: boolean;
}
