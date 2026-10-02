import Link from "next/link";
import { notFound } from "next/navigation";

import { AgentTabs } from "@/components/agents/agent-tabs";
import { RuntimeDown } from "@/components/runtime-down";
import { ApiError, api, apiReachable } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AgentLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}) {
  if (!(await apiReachable())) return <RuntimeDown />;
  const { slug } = await params;

  const agent = await api.agent(slug).catch((error) => {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  });
  if (!agent) notFound();

  return (
    <>
      <header className="flex items-center gap-4 border-b border-border px-6 py-3">
        <div className="flex min-w-0 items-center gap-2 text-sm">
          <Link href="/" className="shrink-0 text-muted-foreground hover:text-foreground">
            Agents
          </Link>
          <span className="text-muted-foreground/50">/</span>
          <span className="truncate font-medium">{agent.name}</span>
          <span className="shrink-0 rounded-md border border-border bg-surface px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
            v{agent.version}
          </span>
        </div>
        <div className="ml-auto">
          <AgentTabs slug={slug} />
        </div>
      </header>
      {children}
    </>
  );
}
