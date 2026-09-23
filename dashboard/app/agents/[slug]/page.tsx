import { notFound } from "next/navigation";

import { AgentEditor } from "@/components/canvas/agent-editor";
import { RuntimeDown } from "@/components/runtime-down";
import { ApiError, api, apiReachable } from "@/lib/api";

export const dynamic = "force-dynamic";

async function load(slug: string) {
  try {
    const [agent, providers, versions] = await Promise.all([
      api.agent(slug),
      api.providers(),
      api.versions(slug),
    ]);
    return { agent, providers, versions };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  if (!(await apiReachable())) return <RuntimeDown />;

  const loaded = await load((await params).slug);
  if (!loaded) notFound();

  return (
    <AgentEditor
      providers={loaded.providers}
      config={loaded.agent.config}
      saved={{ slug: loaded.agent.slug, version: loaded.agent.version }}
      versions={loaded.versions}
    />
  );
}
