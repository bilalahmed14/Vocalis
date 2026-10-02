import { AgentSettings } from "@/components/agents/agent-settings";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const agent = await api.agent(slug);
  return <AgentSettings slug={slug} config={agent.config} />;
}
