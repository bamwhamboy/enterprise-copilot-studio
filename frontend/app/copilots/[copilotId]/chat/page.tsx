import { ChatWorkspace } from "@/components/chat/chat-workspace";

export default async function CopilotChatPage({
  params,
  searchParams,
}: {
  params: Promise<{ copilotId: string }>;
  searchParams: Promise<{ documentId?: string }>;
}) {
  const { copilotId } = await params;
  // Fix #2C: explicit document scope, e.g. from a "Chat with this
  // document" link (see components/knowledge-sources/knowledge-source-detail.tsx).
  // Absent for ordinary, unscoped copilot chat -- unchanged behavior.
  const { documentId } = await searchParams;
  return <ChatWorkspace copilotId={copilotId} documentId={documentId} />;
}
