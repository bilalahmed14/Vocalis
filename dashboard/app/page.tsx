import { Plus, Waypoints } from "lucide-react";
import Link from "next/link";

import { AgentCard } from "@/components/agents/agent-card";
import { RuntimeDown } from "@/components/runtime-down";
import { PageHeader } from "@/components/shell/page-header";
import { api, apiReachable } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Page() {
  if (!(await apiReachable())) return <RuntimeDown />;

  const agents = await api.agents();

  return (
    <>
      <PageHeader title="Agents" subtitle="Voice agents you've built and saved.">
        <Link
          href="/new"
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <Plus className="size-4" />
          New agent
        </Link>
      </PageHeader>

      <div className="min-h-0 flex-1 overflow-y-auto px-8 py-6">
        {agents.length ? (
          <div className="mx-auto grid max-w-4xl gap-2.5">
            {agents.map((agent) => (
              <AgentCard key={agent.slug} agent={agent} />
            ))}
          </div>
        ) : (
          <div className="mx-auto mt-20 flex max-w-sm flex-col items-center text-center">
            <span className="flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary ring-1 ring-primary/20">
              <Waypoints className="size-6" />
            </span>
            <h2 className="mt-4 font-medium">No agents yet</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Patch a VAD, speech-to-text, a model and a voice together, then save it.
            </p>
            <Link
              href="/new"
              className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground"
            >
              <Plus className="size-4" />
              Build your first agent
            </Link>
          </div>
        )}
      </div>
    </>
  );
}
