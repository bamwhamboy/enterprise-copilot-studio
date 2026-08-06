import {
  LayoutDashboard,
  Store,
  Wand2,
  Bot,
  Database,
  FileStack,
  Blocks,
  Gauge,
  Wallet,
  BarChart3,
  Settings,
  HelpCircle,
} from "lucide-react";
import type { NavItem } from "@/types/nav";

/**
 * Primary sidebar navigation. Central source of truth so the sidebar,
 * mobile drawer, and command palette (future) all stay in sync.
 */
export const primaryNavItems: NavItem[] = [
  { key: "dashboard", label: "Dashboard", href: "/", icon: LayoutDashboard },
  {
    key: "copilots",
    label: "Copilots",
    href: "/copilots",
    icon: Bot,
  },
  {
    key: "marketplace",
    label: "Copilot Marketplace",
    href: "/marketplace",
    icon: Store,
  },
  {
    key: "composer",
    label: "Copilot Composer",
    href: "/composer",
    icon: Wand2,
  },
  {
    key: "knowledge-sources",
    label: "Knowledge Sources",
    href: "/knowledge-sources",
    icon: Database,
  },
  {
    key: "documents",
    label: "Documents",
    href: "/documents",
    icon: FileStack,
  },
  {
    key: "ai-components",
    label: "AI Components",
    href: "/ai-components",
    icon: Blocks,
  },
  {
    key: "ai-optimizer",
    label: "AI Optimizer",
    href: "/ai-optimizer",
    icon: Gauge,
  },
  {
    key: "cost-dashboard",
    label: "Cost Dashboard",
    href: "/cost-dashboard",
    icon: Wallet,
  },
  {
    key: "analytics",
    label: "Analytics",
    href: "/analytics",
    icon: BarChart3,
  },
];

/** Secondary/footer navigation, visually separated from the primary group. */
export const secondaryNavItems: NavItem[] = [
  { key: "settings", label: "Settings", href: "/settings", icon: Settings },
  { key: "help", label: "Help", href: "/help", icon: HelpCircle },
];
