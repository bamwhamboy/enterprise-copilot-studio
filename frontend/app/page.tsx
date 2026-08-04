import Link from "next/link";
import {
  Bot,
  Zap,
  Wallet,
  Timer,
  Router,
  SearchCode,
  Boxes,
  Database,
  Users,
  Building2,
  Landmark,
  Laptop,
  Coins,
  Gauge,
  FileStack,
  ShieldCheck,
  PiggyBank,
  Sparkles,
  Rocket,
  BookOpenCheck,
  ArrowUpRight,
} from "lucide-react";

import type {
  StatCardData,
  PlatformHealthData,
  MarketplaceCopilotData,
  OptimizerMetricData,
  ActivityItemData,
} from "@/types/dashboard";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { WelcomeBanner } from "@/components/dashboard/welcome-banner";
import { StatCard } from "@/components/dashboard/stat-card";
import { DashboardSection } from "@/components/dashboard/dashboard-section";
import { PlatformHealthCard } from "@/components/dashboard/platform-health-card";
import { MarketplaceCopilotCard } from "@/components/dashboard/marketplace-copilot-card";
import { OptimizerMetricTile } from "@/components/dashboard/optimizer-metric-tile";
import { ActivityTimeline } from "@/components/dashboard/activity-timeline";

// ---- Mock data -------------------------------------------------------
// UI foundation only — replace with real queries once the platform API exists.

const kpiCards: StatCardData[] = [
  {
    id: "active-copilots",
    label: "Active Copilots",
    value: "6",
    icon: Bot,
    trendLabel: "+2 this month",
    trendDirection: "up",
  },
  {
    id: "ai-requests-today",
    label: "AI Requests Today",
    value: "12,480",
    icon: Zap,
    trendLabel: "+8.4% vs yesterday",
    trendDirection: "up",
  },
  {
    id: "monthly-cost",
    label: "Monthly AI Cost",
    value: "$4,215",
    icon: Wallet,
    trendLabel: "-6.1% vs last month",
    trendDirection: "down",
  },
  {
    id: "avg-response-time",
    label: "Average Response Time",
    value: "820ms",
    icon: Timer,
    trendLabel: "Within SLA",
    trendDirection: "flat",
  },
];

const platformHealth: PlatformHealthData[] = [
  {
    id: "llm-gateway",
    name: "LLM Gateway",
    description: "LiteLLM routing layer",
    status: "healthy",
    icon: Router,
    lastUpdated: "Just now",
  },
  {
    id: "retrieval-engine",
    name: "Retrieval Engine",
    description: "Hierarchical Hybrid RAG",
    status: "healthy",
    icon: SearchCode,
    lastUpdated: "Just now",
  },
  {
    id: "vector-db",
    name: "Vector Database",
    description: "Qdrant cluster",
    status: "degraded",
    icon: Boxes,
    lastUpdated: "2 min ago",
  },
  {
    id: "redis",
    name: "Redis",
    description: "Semantic + session cache",
    status: "healthy",
    icon: Zap,
    lastUpdated: "1 min ago",
  },
  {
    id: "postgresql",
    name: "PostgreSQL",
    description: "Primary application database",
    status: "healthy",
    icon: Database,
    lastUpdated: "Just now",
  },
];

const marketplaceCopilots: MarketplaceCopilotData[] = [
  {
    id: "hr-copilot",
    name: "HR Copilot",
    description: "Policies, leave, and onboarding assistant.",
    category: "Human Resources",
    icon: Users,
    status: "available",
    // No dedicated HR Copilot page exists yet — route into the wizard that creates/configures it.
    href: "/create-copilot",
  },
  {
    id: "finance-copilot",
    name: "Finance Copilot",
    description: "Expense, budget, and reporting assistant.",
    category: "Finance",
    icon: Landmark,
    status: "coming-soon",
    href: "/marketplace",
  },
  {
    id: "procurement-copilot",
    name: "Procurement Copilot",
    description: "Vendor, contract, and sourcing assistant.",
    category: "Procurement",
    icon: Building2,
    status: "coming-soon",
    href: "/marketplace",
  },
  {
    id: "it-copilot",
    name: "IT Copilot",
    description: "Access requests and troubleshooting assistant.",
    category: "IT",
    icon: Laptop,
    status: "coming-soon",
    href: "/marketplace",
  },
];

const optimizerMetrics: OptimizerMetricData[] = [
  {
    id: "token-savings",
    label: "Token Savings",
    value: "34%",
    progress: 34,
    icon: Coins,
    description: "Reduced via prompt and context optimization.",
  },
  {
    id: "cache-hit-ratio",
    label: "Cache Hit Ratio",
    value: "61%",
    progress: 61,
    icon: Gauge,
    description: "Requests served from the semantic cache.",
  },
  {
    id: "context-compression",
    label: "Context Compression",
    value: "42%",
    progress: 42,
    icon: FileStack,
    description: "Average reduction in retrieved context size.",
  },
  {
    id: "prompt-sanitization",
    label: "Prompt Sanitization",
    value: "128 blocked",
    icon: ShieldCheck,
    description: "Unsafe or injected prompts blocked this month.",
  },
];

const activityItems: ActivityItemData[] = [
  {
    id: "a1",
    title: "HR Copilot v1.3 generated",
    description: "Composed from 4 AI components and 2 knowledge sources.",
    timestamp: "10 min ago",
    icon: Sparkles,
    status: "success",
  },
  {
    id: "a2",
    title: "Finance Copilot draft created",
    description: "Template scaffolded, pending knowledge source setup.",
    timestamp: "1 hr ago",
    icon: Rocket,
    status: "info",
  },
  {
    id: "a3",
    title: "Knowledge source re-indexed",
    description: "Policies_2026.pdf embedded and added to the retrieval index.",
    timestamp: "3 hr ago",
    icon: BookOpenCheck,
    status: "info",
  },
  {
    id: "a4",
    title: "Cost threshold notice",
    description: "IT Copilot sandbox crossed 80% of its monthly budget.",
    timestamp: "Yesterday",
    icon: PiggyBank,
    status: "warning",
  },
];

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-8">
      <WelcomeBanner />

      <DashboardSection title="Key Metrics" description="Live snapshot across your copilot platform.">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {kpiCards.map((card) => (
            <StatCard key={card.id} data={card} />
          ))}
        </div>
      </DashboardSection>

      <DashboardSection
        title="Platform Health"
        description="Core infrastructure services powering every copilot."
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {platformHealth.map((service) => (
            <PlatformHealthCard key={service.id} data={service} />
          ))}
        </div>
      </DashboardSection>

      <div className="grid grid-cols-1 gap-8 xl:grid-cols-3">
        <div className="flex flex-col gap-8 xl:col-span-2">
          <DashboardSection
            title="Copilot Marketplace"
            description="Ready-made templates for every business function."
            action={
              <Button variant="ghost" size="sm" asChild>
                <Link href="/marketplace">
                  Browse all
                  <ArrowUpRight className="size-3.5" />
                </Link>
              </Button>
            }
          >
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {marketplaceCopilots.map((copilot) => (
                <MarketplaceCopilotCard key={copilot.id} data={copilot} />
              ))}
            </div>
          </DashboardSection>

          <DashboardSection
            title="AI Optimizer"
            description="Cost and performance gains from the optimization layer."
          >
            <Card className="overflow-hidden">
              <CardContent className="flex flex-col gap-6 pt-6">
                <div className="flex flex-col gap-1 rounded-xl bg-gradient-to-br from-primary/10 to-[#5b7cfa]/10 p-5 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                      <PiggyBank className="size-5" />
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">
                        Estimated Monthly Savings
                      </p>
                      <p className="text-2xl font-semibold tracking-tight text-foreground">
                        $1,860
                      </p>
                    </div>
                  </div>
                  <span className="w-fit rounded-full bg-success/15 px-2.5 py-1 text-xs font-medium text-success">
                    30% below unoptimized baseline
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {optimizerMetrics.map((metric) => (
                    <OptimizerMetricTile key={metric.id} data={metric} />
                  ))}
                </div>
              </CardContent>
            </Card>
          </DashboardSection>
        </div>

        <DashboardSection
          title="Recent Activity"
          description="Latest copilot generation events."
        >
          <Card>
            <CardContent className="pt-6">
              <ActivityTimeline items={activityItems} />
            </CardContent>
          </Card>
        </DashboardSection>
      </div>
    </div>
  );
}
