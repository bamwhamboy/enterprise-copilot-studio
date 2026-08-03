"use client";

import { useSyncExternalStore } from "react";
import { motion } from "framer-motion";
import {
  Sparkles,
  ChevronDown,
  Plus,
  Database,
  UserPlus,
  BookOpen,
} from "lucide-react";

import type { QuickAction } from "@/types/dashboard";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const quickActions: QuickAction[] = [
  { id: "new-copilot", label: "Create Copilot", icon: Plus },
  { id: "add-source", label: "Add Knowledge Source", icon: Database },
  { id: "invite", label: "Invite Teammate", icon: UserPlus },
  { id: "docs", label: "View Documentation", icon: BookOpen },
];

function getGreeting(hour: number) {
  if (hour < 5) return "Good night";
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

const emptySubscribe = () => () => {};

export function WelcomeBanner() {
  // Server snapshot stays neutral (no Date access); client snapshot resolves
  // the real time-based greeting once hydrated. Avoids setState-in-effect
  // and any server/client mismatch.
  const clientGreeting = useSyncExternalStore(
    emptySubscribe,
    () => getGreeting(new Date().getHours()),
    () => null
  );
  const greeting = clientGreeting ?? "Welcome back";

  return (
    <div className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-primary/10 via-card to-[#5b7cfa]/10 p-6 sm:p-8">
      <div className="pointer-events-none absolute -right-16 -top-24 size-64 rounded-full bg-primary/20 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 left-1/3 size-56 rounded-full bg-[#5b7cfa]/15 blur-3xl" />

      <div className="relative flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="flex flex-col gap-2"
        >
          <span className="inline-flex w-fit items-center gap-1.5 rounded-full border border-primary/20 bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
            <Sparkles className="size-3.5" />
            Enterprise Copilot Studio
          </span>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
            {greeting}, Vijay
          </h1>
          <p className="max-w-md text-sm text-muted-foreground">
            Here&apos;s how your copilot platform is performing today.
          </p>
        </motion.div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button size="lg" className="w-fit shadow-sm">
              Quick Actions
              <ChevronDown className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            {quickActions.map((action) => (
              <DropdownMenuItem key={action.id}>
                <action.icon />
                {action.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
