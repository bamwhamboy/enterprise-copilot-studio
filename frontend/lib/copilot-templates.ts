import {
  Users,
  Landmark,
  Laptop,
  Scale,
  FlaskConical,
  HeartPulse,
  Headset,
  Building2,
  Truck,
  Briefcase,
} from "lucide-react";

import type { CopilotTemplate } from "@/types/copilot-template";

/**
 * Mapped onto the backend's real, constrained domain enum (hr | finance |
 * procurement | sales | legal | it | analytics) -- there's no backend
 * support for inventing new domains, so templates without an exact match
 * (e.g. "Clinical Research Assistant") are mapped to the closest real
 * bucket while keeping their own distinct name/description/icon for
 * visual variety, and marked unavailable (shown in Marketplace's
 * "Coming Soon" section) since that mapping is an approximation, not a
 * confident 1:1 match.
 */
export const copilotTemplates: CopilotTemplate[] = [
  {
    id: "hr-assistant",
    name: "HR Assistant",
    description: "Answers employee questions on policy, leave, and onboarding.",
    domain: "hr",
    icon: Users,
    accent: "from-violet-500/15 to-purple-500/15 text-violet-600 dark:text-violet-400",
    available: true,
  },
  {
    id: "finance-analyst",
    name: "Finance Analyst",
    description: "Summarizes reports, budgets, and financial policy documents.",
    domain: "finance",
    icon: Landmark,
    accent: "from-emerald-500/15 to-teal-500/15 text-emerald-600 dark:text-emerald-400",
    available: true,
  },
  {
    id: "it-support",
    name: "IT Support",
    description: "Troubleshoots access requests and internal tooling issues.",
    domain: "it",
    icon: Laptop,
    accent: "from-sky-500/15 to-blue-500/15 text-sky-600 dark:text-sky-400",
    available: true,
  },
  {
    id: "legal-advisor",
    name: "Legal Advisor",
    description: "Grounded answers on contracts, compliance, and legal policy.",
    domain: "legal",
    icon: Scale,
    accent: "from-slate-500/15 to-zinc-500/15 text-slate-600 dark:text-slate-300",
    available: true,
  },
  {
    id: "procurement-assistant",
    name: "Procurement Assistant",
    description: "Guides vendor selection, contracts, and sourcing policy.",
    domain: "procurement",
    icon: Building2,
    accent: "from-indigo-500/15 to-violet-500/15 text-indigo-600 dark:text-indigo-400",
    available: true,
  },
  {
    id: "clinical-research",
    name: "Clinical Research Assistant",
    description: "Surfaces findings and protocols from research documentation.",
    domain: "analytics",
    icon: FlaskConical,
    accent: "from-cyan-500/15 to-sky-500/15 text-cyan-600 dark:text-cyan-400",
    available: false,
  },
  {
    id: "medical-knowledge",
    name: "Medical Knowledge Assistant",
    description: "Answers clinical questions grounded in medical documentation.",
    domain: "analytics",
    icon: HeartPulse,
    accent: "from-rose-500/15 to-red-500/15 text-rose-600 dark:text-rose-400",
    available: false,
  },
  {
    id: "customer-success",
    name: "Customer Success Bot",
    description: "Helps customer-facing teams answer product and account questions.",
    domain: "sales",
    icon: Headset,
    accent: "from-amber-500/15 to-orange-500/15 text-amber-600 dark:text-amber-400",
    available: false,
  },
  {
    id: "supply-chain",
    name: "Supply Chain Copilot",
    description: "Answers questions on logistics, inventory, and supplier policy.",
    domain: "procurement",
    icon: Truck,
    accent: "from-lime-500/15 to-green-500/15 text-lime-600 dark:text-lime-400",
    available: false,
  },
  {
    id: "executive-assistant",
    name: "Executive Assistant",
    description: "A cross-functional copilot for leadership and strategy questions.",
    domain: "analytics",
    icon: Briefcase,
    accent: "from-fuchsia-500/15 to-pink-500/15 text-fuchsia-600 dark:text-fuchsia-400",
    available: false,
  },
];
