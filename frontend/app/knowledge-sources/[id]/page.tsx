import { KnowledgeSourceDetail } from "@/components/knowledge-sources/knowledge-source-detail";

export default async function KnowledgeSourceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <KnowledgeSourceDetail knowledgeSourceId={id} />;
}
