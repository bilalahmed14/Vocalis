import { ArrowRight, Plus } from "lucide-react";
import Link from "next/link";

import { CallTable } from "@/components/calls/call-table";
import { LatencyTrend } from "@/components/calls/latency-trend";
import { StageBars } from "@/components/calls/stage-bars";
import { Stat } from "@/components/calls/stat";
import { RuntimeDown } from "@/components/runtime-down";
import { PageHeader } from "@/components/shell/page-header";
import { api, apiReachable } from "@/lib/api";
import { ms } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function Page() {
  if (!(await apiReachable())) return <RuntimeDown />;

  const stats = await api.overview();

  return (
    <>
      <PageHeader title="Overview" subtitle="Where the milliseconds went, across every call this fortnight.">
        <Link
          href="/new"
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <Plus className="size-4" />
          New agent
        </Link>
      </PageHeader>

      <div className="min-h-0 flex-1 overflow-y-auto px-8 py-6">
        <div className="mx-auto max-w-5xl space-y-6">
          <div className="grid gap-6 border-y border-border py-5 sm:grid-cols-4">
            <Stat label="Agents" value={String(stats.agents)} />
            <Stat label="Calls" value={String(stats.calls)} hint="last 14 days" />
            <Stat label="Typical turn" value={ms(stats.p50_ms)} hint="p50 to first audio" />
            <Stat label="Worst turns" value={ms(stats.p95_ms)} hint="p95 to first audio" />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <section>
              <h2 className="display text-lg leading-none">Time to first audio</h2>
              <p className="mb-4 mt-1.5 text-xs text-muted-foreground">
                Median per day. Lower is a caller waiting less after they stop speaking.
              </p>
              <LatencyTrend daily={stats.daily} />
            </section>

            <section>
              <h2 className="display text-lg leading-none">Where the time goes</h2>
              <p className="mb-4 mt-1.5 text-xs text-muted-foreground">
                Median cost of each stage across recent turns — the top row is what to fix first.
              </p>
              <StageBars stages={stats.slowest_stages} />
            </section>
          </div>

          {stats.turns > 0 ? (
            <p className="text-xs text-muted-foreground">
              {Math.round(stats.interrupted_share * 100)}% of turns were interrupted. On speakers
              that is usually the agent hearing itself.
            </p>
          ) : null}

          <section className="space-y-3">
            <div className="flex items-baseline justify-between">
              <h2 className="display text-lg leading-none">Recent calls</h2>
              <Link
                href="/calls"
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                All calls <ArrowRight className="size-3" />
              </Link>
            </div>
            <CallTable calls={stats.recent} />
          </section>
        </div>
      </div>
    </>
  );
}
