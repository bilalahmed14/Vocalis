import Link from "next/link";

import { RuntimeDown } from "@/components/runtime-down";
import { api, apiReachable } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Page() {
  if (!(await apiReachable())) return <RuntimeDown />;

  const agents = await api.agents();

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Vocalis</h1>
          <p className="text-sm text-muted-foreground">
            Patch STT, LLM and TTS providers together, then call the agent.
          </p>
        </div>
        <Link
          href="/new"
          className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground"
        >
          New agent
        </Link>
      </div>

      <ul className="mt-8 divide-y rounded-lg border">
        {agents.map((agent) => (
          <li key={agent.slug}>
            <Link href={`/agents/${agent.slug}`} className="flex items-center gap-3 px-4 py-3 hover:bg-accent">
              <span className="flex-1 font-medium">{agent.name}</span>
              <span className="text-xs text-muted-foreground">v{agent.version}</span>
              <span className="text-xs text-muted-foreground">
                {new Date(agent.updated_at).toLocaleDateString()}
              </span>
            </Link>
          </li>
        ))}
        {agents.length === 0 ? (
          <li className="px-4 py-8 text-center text-sm text-muted-foreground">
            No agents yet. Start with <Link href="/new" className="underline">a new one</Link>.
          </li>
        ) : null}
      </ul>
    </main>
  );
}
