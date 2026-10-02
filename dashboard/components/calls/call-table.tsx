import { ChevronRight, TriangleAlert } from "lucide-react";
import Link from "next/link";

import type { CallLog } from "@/lib/api";
import { duration, ms, timeAgo } from "@/lib/format";

export function CallTable({ calls, showAgent = true }: { calls: CallLog[]; showAgent?: boolean }) {
  if (!calls.length) {
    return (
      <div className="border-y border-dashed border-border px-6 py-12 text-center">
        <p className="display text-lg">No calls yet</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Open an agent and press Test call; every call is logged here with its timings.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden border-y border-border">
      <table className="w-full text-sm">
        <thead className="border-b border-border">
          <tr>
            {showAgent ? <th className="silkscreen px-4 py-2 text-left">Agent</th> : null}
            <th className="silkscreen px-4 py-2 text-left">When</th>
            <th className="silkscreen px-4 py-2 text-right">Length</th>
            <th className="silkscreen px-4 py-2 text-right">Turns</th>
            <th className="silkscreen px-4 py-2 text-right">p50</th>
            <th className="silkscreen px-4 py-2 text-right">p95</th>
            <th className="w-8" />
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60">
          {calls.map((call) => (
            <tr key={call.id} className="group hover:bg-accent/40">
              {showAgent ? (
                <td className="px-4 py-2.5">
                  <Link href={`/calls/${call.id}`} className="font-medium hover:underline">
                    {call.agent_name}
                  </Link>
                  {call.agent_version ? (
                    <span className="ml-1.5 font-mono text-[11px] text-muted-foreground">
                      v{call.agent_version}
                    </span>
                  ) : null}
                </td>
              ) : null}
              <td className="px-4 py-2.5 text-muted-foreground">
                <Link href={`/calls/${call.id}`} className="hover:underline">
                  {timeAgo(call.started_at)}
                </Link>
              </td>
              <td className="readout px-4 py-2.5 text-right text-muted-foreground">
                {duration(call.started_at, call.ended_at)}
              </td>
              <td className="readout px-4 py-2.5 text-right">
                {call.turn_count}
                {call.interrupted_turns ? (
                  <span
                    className="ml-1.5 inline-flex items-center gap-0.5 text-[11px] text-muted-foreground"
                    title={`${call.interrupted_turns} interrupted`}
                  >
                    <TriangleAlert className="size-3" />
                    {call.interrupted_turns}
                  </span>
                ) : null}
              </td>
              <td className="readout px-4 py-2.5 text-right">{ms(call.p50_ms)}</td>
              <td className="readout px-4 py-2.5 text-right text-muted-foreground">
                {ms(call.p95_ms)}
              </td>
              <td className="px-2 py-2.5">
                <Link href={`/calls/${call.id}`}>
                  <ChevronRight className="size-4 text-muted-foreground group-hover:text-foreground" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
