import { ChatWorkspace } from "@/components/chat/chat-workspace";

export default async function CopilotChatPage({
  params,
}: {
  params: Promise<{ copilotId: string }>;
}) {
  const { copilotId } = await params;
  return <ChatWorkspace copilotId={copilotId} />;
}
