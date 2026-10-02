import { ArrowLeft, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Stat } from "@/components/calls/stat";
import { TurnWaterfall } from "@/components/calls/turn-waterfall";
import { RuntimeDown } from "@/components/runtime-down";
import { ApiError, api, apiReachable } from "@/lib/api";
import { duration, ms } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  if (!(await apiReachable())) return <RuntimeDown />;
  const { id } = await params;

  const detail = await api.log(id).catch((error) => {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  });
  if (!detail) notFound();

  const { call, turns, messages } = detail;
  const slowest = [...turns].sort((a, b) => b.total_ms - a.total_ms)[0];

  return (
    <>
      <header className="flex items-center gap-3 border-b border-border px-6 py-3">
        <Link href="/calls" className="text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-4" />
        </Link>
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{call.agent_name}</div>
          <div className="text-xs text-muted-foreground">
            {new Date(call.started_at).toLocaleString()}
            {call.agent_slug ? (
              <>
                {" · "}
                <Link href={`/agents/${call.agent_slug}`} className="hover:underline">
                  open agent
                </Link>
              </>
            ) : null}
          </div>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
        <div className="mx-auto max-w-5xl space-y-6">
          <div className="grid gap-3 sm:grid-cols-4">
            <Stat label="Turns" value={String(call.turn_count)} />
            <Stat label="p50" value={ms(call.p50_ms)} hint="to first audio" />
            <Stat label="p95" value={ms(call.p95_ms)} hint="to first audio" />
            <Stat label="Length" value={duration(call.started_at, call.ended_at)} />
          </div>

          {call.interrupted_turns ? (
            <p className="flex items-center gap-2 rounded-lg border border-border bg-surface px-4 py-2.5 text-xs text-muted-foreground">
              <TriangleAlert className="size-3.5 shrink-0" />
              {call.interrupted_turns} of {call.turn_count} replies were cut off. On speakers that
              is usually the agent hearing itself; with headphones it means you spoke over it.
            </p>
          ) : null}

          <section className="grid gap-6 lg:grid-cols-[1fr_20rem]">
            <div className="space-y-3">
              <h2 className="text-sm font-medium">
                Turns
                {slowest ? (
                  <span className="ml-2 text-xs font-normal text-muted-foreground">
                    slowest {slowest.total_ms} ms
                  </span>
                ) : null}
              </h2>

              {turns.map((turn) => (
                <div key={turn.turn} className="rounded-xl border border-border bg-card p-4">
                  <div className="mb-2 flex items-baseline gap-2 text-xs">
                    <span className="font-medium">Turn {turn.turn}</span>
                    <span className="font-mono">{turn.total_ms} ms</span>
                    <span className="text-muted-foreground">to first audio</span>
                    {turn.interrupted ? (
                      <span className="ml-auto text-muted-foreground">interrupted</span>
                    ) : null}
                  </div>
                  <TurnWaterfall stages={turn.stages} />
                </div>
              ))}

              {turns.length === 0 ? (
                <p className="rounded-xl border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                  No turns were measured. The call may have ended before the agent replied.
                </p>
              ) : null}
            </div>

            <div>
              <h2 className="mb-3 text-sm font-medium">Transcript</h2>
              <div className="space-y-2 rounded-xl border border-border bg-card p-4">
                {messages.map((message, index) => (
                  <div key={index} className="flex gap-2 text-sm">
                    <span
                      className={
                        message.role === "user"
                          ? "shrink-0 text-muted-foreground"
                          : "shrink-0 font-medium text-primary"
                      }
                    >
                      {message.role === "user" ? "you" : "agent"}
                    </span>
                    <span className="min-w-0">
                      {message.text}
                      {message.interrupted ? (
                        <span className="ml-1 text-[11px] text-muted-foreground">[cut off]</span>
                      ) : null}
                    </span>
                  </div>
                ))}
                {messages.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Nothing was said.</p>
                ) : null}
              </div>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
