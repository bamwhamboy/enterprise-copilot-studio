"use client";

import { Database, RefreshCcw, PlugZap, Lock } from "lucide-react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";
import type { KnowledgeDatabase } from "@/types/knowledge-hub";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

export function DatabaseCard({ database }: { database: KnowledgeDatabase }) {
  const isConnected = database.status === "connected";

  return (
    <motion.div whileHover={isConnected ? { y: -2 } : undefined}>
      <Card
        className={cn(
          "h-full transition-shadow",
          isConnected && "hover:shadow-md",
          !isConnected && "bg-muted/30 opacity-80"
        )}
      >
        <CardContent className="flex h-full flex-col gap-4 pt-6">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  "flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary",
                  !isConnected && "grayscale"
                )}
              >
                <Database className="size-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">
                  {database.name}
                </p>
                <p className="text-xs text-muted-foreground">{database.engine}</p>
              </div>
            </div>
            <Badge variant={isConnected ? "success" : "secondary"}>
              {isConnected ? "Connected" : "Coming Soon"}
            </Badge>
          </div>

          <p className="text-xs text-muted-foreground">{database.description}</p>

          <Separator className="mt-auto" />

          {isConnected ? (
            <div className="flex items-center gap-1.5">
              <Button variant="outline" size="sm" className="flex-1">
                <PlugZap className="size-3.5" />
                Test Connection
              </Button>
              <Button variant="outline" size="sm" className="flex-1">
                <RefreshCcw className="size-3.5" />
                Refresh Schema
              </Button>
            </div>
          ) : (
            <Button variant="outline" size="sm" className="w-full" disabled>
              <Lock className="size-3.5" />
              Connect
            </Button>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
