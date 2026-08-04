import { Workflow, Cpu, Boxes, Bot } from "lucide-react";

import type { KnowledgeStatItem, KnowledgeConfigItem } from "@/types/knowledge-hub";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

const stats: KnowledgeStatItem[] = [
  { id: "documents", label: "Documents", value: "148" },
  { id: "chunks", label: "Indexed Chunks", value: "42,381" },
  { id: "embeddings", label: "Embeddings", value: "42,381" },
  { id: "avg-chunk-size", label: "Average Chunk Size", value: "512 tokens" },
];

const configItems: KnowledgeConfigItem[] = [
  { id: "retrieval", label: "Retrieval Strategy", value: "Hierarchical Hybrid RAG", icon: Workflow },
  { id: "embedding-model", label: "Embedding Model", value: "BAAI/bge-small-en-v1.5", icon: Cpu },
  { id: "vector-store", label: "Vector Store", value: "Qdrant", icon: Boxes },
  { id: "llm", label: "LLM", value: "Groq Llama 3", icon: Bot },
];

export function KnowledgeStatsPanel() {
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Knowledge Statistics</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {stats.map((stat, index) => (
            <div key={stat.id}>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{stat.label}</span>
                <span className="font-medium text-foreground">{stat.value}</span>
              </div>
              {index !== stats.length - 1 && <Separator className="mt-3" />}
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-primary/5 to-[#5b7cfa]/5">
        <CardHeader>
          <CardTitle className="text-sm">Platform Configuration</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {configItems.map((item) => (
            <div key={item.id} className="flex items-start gap-2.5">
              <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-card text-primary shadow-sm">
                <item.icon className="size-3.5" />
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">{item.label}</span>
                <span className="text-xs font-medium text-foreground">
                  {item.value}
                </span>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
