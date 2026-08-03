import type { LucideIcon } from "lucide-react";

export interface NavItem {
  /** Unique key, also used to derive the route href */
  key: string;
  label: string;
  href: string;
  icon: LucideIcon;
  /** Optional badge text, e.g. "New" or a count */
  badge?: string;
}

export interface NavSection {
  title?: string;
  items: NavItem[];
}
