import { ChevronRight } from "lucide-react";
import Link from "next/link";

import type { AgentSummary } from "@/lib/api";

function timeAgo(iso: string): string {
  const seconds = Math.max(1, (Date.now() - new Date(iso).getTime()) / 1000);
  const steps: [number, Intl.RelativeTimeFormatUnit][] = [
    [60, "second"],
    [60, "minute"],
    [24, "hour"],
    [7, "day"],
    [4.35, "week"],
    [12, "month"],
  ];

  let value = seconds;
  for (const [size, unit] of steps) {
    if (value < size) {
      return new Intl.RelativeTimeFormat("en", { numeric: "auto" }).format(-Math.round(value), unit);
    }
    value /= size;
  }
  return new Intl.RelativeTimeFormat("en", { numeric: "auto" }).format(-Math.round(value), "year");
}

export function AgentCard({ agent }: { agent: AgentSummary }) {
  return (
    <Link
      href={`/agents/${agent.slug}`}
      className="group flex items-center gap-4 rounded-xl border border-border bg-card px-5 py-4 transition-colors hover:border-primary/40 hover:bg-accent/40"
    >
      <div className="min-w-0 flex-1">
        <div className="truncate font-medium">{agent.name}</div>
        <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-mono">{agent.slug}</span>
          <span aria-hidden>·</span>
          <span>edited {timeAgo(agent.updated_at)}</span>
        </div>
      </div>

      <span className="rounded-md border border-border bg-surface px-2 py-1 font-mono text-[11px] text-muted-foreground">
        v{agent.version}
      </span>
      <ChevronRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-foreground" />
    </Link>
  );
}
