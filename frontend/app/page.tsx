import {
  Bot,
  Users,
  Zap,
  Wallet,
  Activity,
  Store,
  HeartPulse,
  LineChart,
} from "lucide-react";

import type { StatCardData } from "@/types/dashboard";
import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/dashboard/stat-card";
import { PlaceholderSection } from "@/components/dashboard/placeholder-section";

const statCards: StatCardData[] = [
  {
    id: "active-copilots",
    label: "Active Copilots",
    value: "—",
    icon: Bot,
    trendLabel: "Awaiting data",
    trendDirection: "flat",
  },
  {
    id: "total-users",
    label: "Total Users",
    value: "—",
    icon: Users,
    trendLabel: "Awaiting data",
    trendDirection: "flat",
  },
  {
    id: "ai-requests",
    label: "AI Requests",
    value: "—",
    icon: Zap,
    trendLabel: "Awaiting data",
    trendDirection: "flat",
  },
  {
    id: "monthly-cost",
    label: "Monthly Cost",
    value: "—",
    icon: Wallet,
    trendLabel: "Awaiting data",
    trendDirection: "flat",
  },
];

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Dashboard"
        description="Overview of your enterprise copilot platform."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {statCards.map((card) => (
          <StatCard key={card.id} data={card} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <PlaceholderSection
          title="Recent Activity"
          description="Copilot deployments and edits will appear here."
          icon={Activity}
        />
        <PlaceholderSection
          title="Copilot Marketplace"
          description="Featured and trending copilot templates will appear here."
          icon={Store}
        />
        <PlaceholderSection
          title="Platform Health"
          description="Latency, uptime, and error rates will appear here."
          icon={HeartPulse}
        />
        <PlaceholderSection
          title="Cost Analytics"
          description="Spend by copilot and model will appear here."
          icon={LineChart}
        />
      </div>
    </div>
  );
}
