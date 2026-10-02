import { AgentEditor } from "@/components/canvas/agent-editor";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const [agent, providers, versions] = await Promise.all([
    api.agent(slug),
    api.providers(),
    api.versions(slug),
  ]);

  return (
    <AgentEditor
      providers={providers}
      config={agent.config}
      saved={{ slug: agent.slug, version: agent.version }}
      versions={versions}
    />
  );
}
