"use client";

import { Globe, RefreshCcw, ExternalLink } from "lucide-react";
import { motion } from "framer-motion";

import type { KnowledgeWebsite } from "@/types/knowledge-hub";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

export function WebsiteCard({ website }: { website: KnowledgeWebsite }) {
  const isIndexed = website.status === "indexed";

  return (
    <motion.div whileHover={{ y: -2 }}>
      <Card className="h-full transition-shadow hover:shadow-md">
        <CardContent className="flex h-full flex-col gap-4 pt-6">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-3">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary/15 to-[#5b7cfa]/15 text-primary">
                <Globe className="size-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">
                  {website.name}
                </p>
                <p className="text-xs text-muted-foreground">{website.url}</p>
              </div>
            </div>
            <Badge variant={isIndexed ? "success" : "warning"}>
              {isIndexed ? "Indexed" : "Pending"}
            </Badge>
          </div>

          <span className="text-xs text-muted-foreground">
            Last crawled {website.lastCrawled}
          </span>

          <Separator className="mt-auto" />

          <div className="flex items-center gap-1.5">
            <Button variant="outline" size="sm" className="flex-1">
              <RefreshCcw className="size-3.5" />
              Re-index
            </Button>
            <Button variant="outline" size="sm" className="flex-1">
              <ExternalLink className="size-3.5" />
              Open
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
