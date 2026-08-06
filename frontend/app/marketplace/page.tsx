"use client";

import Link from "next/link";
import { Store, ArrowRight, Clock } from "lucide-react";
import { motion } from "framer-motion";

import { copilotTemplates } from "@/lib/copilot-templates";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

/**
 * A gallery of copilot templates -- pre-configured starting points for
 * the Create Copilot wizard (each card deep-links into it). This is
 * distinct from /copilots, which manages the user's own real copilots;
 * this page is a catalog of presets, not a list of live backend entities.
 *
 * Split into two sections: templates with a confident, exact backend
 * domain match get full cards; templates whose domain had to be
 * approximated (see lib/copilot-templates.ts) are grouped into a
 * compact "Coming Soon" strip rather than given the same visual weight
 * as a large card with its own call-to-action.
 */
export default function MarketplacePage() {
  const available = copilotTemplates.filter((t) => t.available);
  const comingSoon = copilotTemplates.filter((t) => !t.available);

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="Copilot Marketplace"
        description="Start from a template built for your team, then customize it in a few guided steps."
        icon={Store}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {available.map((template, index) => (
          <motion.div
            key={template.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: index * 0.04 }}
          >
            <Card className="group h-full overflow-hidden transition-shadow hover:shadow-md">
              <CardContent className="flex h-full flex-col gap-4 pt-6">
                <div
                  className={`flex size-11 items-center justify-center rounded-xl bg-gradient-to-br ${template.accent}`}
                >
                  <template.icon className="size-5" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-foreground">{template.name}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{template.description}</p>
                </div>
                <Button asChild variant="outline" size="sm" className="w-full">
                  <Link href={`/create-copilot?template=${template.id}`}>
                    Use this template
                    <ArrowRight className="size-3.5" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {comingSoon.length > 0 && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Clock className="size-4 text-muted-foreground" />
            <h2 className="text-sm font-medium text-foreground">Coming Soon</h2>
          </div>
          <Card>
            <CardContent className="flex flex-wrap gap-2 pt-6">
              {comingSoon.map((template) => (
                <div
                  key={template.id}
                  className="flex items-center gap-2 rounded-full border border-border bg-muted/40 px-3 py-1.5"
                  title={template.description}
                >
                  <template.icon className="size-3.5 text-muted-foreground" />
                  <span className="text-xs font-medium text-foreground">{template.name}</span>
                  <Badge variant="secondary" className="text-[10px]">
                    Soon
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
