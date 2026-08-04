"use client";

import {
  Users,
  Landmark,
  Building2,
  TrendingUp,
  Scale,
  Laptop,
  BarChart3,
  Lock,
  Info,
} from "lucide-react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";
import type { DomainOption } from "@/types/create-copilot";
import { useCreateCopilotStore } from "@/app/create-copilot/store/create-copilot-store";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const domainOptions: DomainOption[] = [
  { id: "hr", label: "HR", icon: Users, available: true },
  { id: "finance", label: "Finance", icon: Landmark, available: false },
  { id: "procurement", label: "Procurement", icon: Building2, available: false },
  { id: "sales", label: "Sales", icon: TrendingUp, available: false },
  { id: "legal", label: "Legal", icon: Scale, available: false },
  { id: "it", label: "IT", icon: Laptop, available: false },
  { id: "analytics", label: "Analytics", icon: BarChart3, available: false },
];

export function StepBasicInformation() {
  const { basicInfo, setName, setDescription, setDomain } =
    useCreateCopilotStore();

  return (
    <div className="flex flex-col gap-8">
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <label
            htmlFor="copilot-name"
            className="text-sm font-medium text-foreground"
          >
            Copilot Name
          </label>
          <Input
            id="copilot-name"
            placeholder="e.g. HR Copilot"
            value={basicInfo.name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-2 sm:col-span-2">
          <label
            htmlFor="copilot-description"
            className="text-sm font-medium text-foreground"
          >
            Description
          </label>
          <Textarea
            id="copilot-description"
            placeholder="Describe what this copilot helps employees do..."
            value={basicInfo.description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground">Domain</span>
          <Tooltip delayDuration={150}>
            <TooltipTrigger asChild>
              <Info className="size-3.5 cursor-help text-muted-foreground" />
            </TooltipTrigger>
            <TooltipContent side="right" className="max-w-64">
              Additional domains will be supported in future releases. For
              this MVP, only HR Copilots can be created.
            </TooltipContent>
          </Tooltip>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {domainOptions.map((domain) => {
            const isSelected = basicInfo.domain === domain.id;

            const cardInner = (
              <button
                type="button"
                disabled={!domain.available}
                onClick={() => domain.available && setDomain(domain.id)}
                className={cn(
                  "group relative flex w-full flex-col items-center gap-2 rounded-xl border border-border bg-card px-3 py-4 text-center transition-all",
                  domain.available &&
                    "cursor-pointer hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md",
                  isSelected &&
                    "border-primary bg-primary/5 ring-2 ring-primary/20",
                  !domain.available && "cursor-not-allowed opacity-50"
                )}
              >
                {!domain.available && (
                  <Lock className="absolute right-2 top-2 size-3 text-muted-foreground" />
                )}
                <div
                  className={cn(
                    "flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary",
                    !domain.available && "grayscale"
                  )}
                >
                  <domain.icon className="size-4" />
                </div>
                <span className="text-xs font-medium text-foreground">
                  {domain.label}
                </span>
                {!domain.available && (
                  <span className="text-[10px] font-medium text-muted-foreground">
                    Coming Soon
                  </span>
                )}
              </button>
            );

            return (
              <motion.div
                key={domain.id}
                whileHover={domain.available ? { y: -1 } : undefined}
              >
                {domain.available ? (
                  cardInner
                ) : (
                  <Tooltip delayDuration={150}>
                    <TooltipTrigger asChild>{cardInner}</TooltipTrigger>
                    <TooltipContent side="top">
                      Additional domains will be supported in future releases.
                    </TooltipContent>
                  </Tooltip>
                )}
              </motion.div>
            );
          })}
        </div>
      </div>

      <Card className="border-dashed bg-muted/30">
        <CardContent className="flex items-start gap-3 pt-6 text-sm text-muted-foreground">
          <Info className="mt-0.5 size-4 shrink-0" />
          <p>
            This MVP focuses on the HR domain. Finance, Procurement, Sales,
            Legal, IT, and Analytics copilots are on the roadmap and will
            reuse the same underlying AI components.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
