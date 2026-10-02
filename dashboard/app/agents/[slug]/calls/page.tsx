import { CallTable } from "@/components/calls/call-table";
import { Stat } from "@/components/calls/stat";
import { api } from "@/lib/api";
import { ms } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const [calls, stats] = await Promise.all([api.logs(slug), api.callStats(slug)]);

  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
      <div className="mx-auto max-w-5xl space-y-5">
        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label="Calls" value={String(stats.calls)} />
          <Stat label="Turns" value={String(stats.turns)} />
          <Stat
            label="Typical turn"
            value={ms(stats.median_ms)}
            hint="median of each call's p50"
          />
        </div>

        <CallTable calls={calls} showAgent={false} />
      </div>
    </div>
  );
}
