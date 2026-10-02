import type { CallStage } from "@/lib/api";
import { throughputLabel } from "@/lib/throughput";

/** One turn's stages as bars, in the order they happened. */
export function TurnWaterfall({ stages }: { stages: CallStage[] }) {
  const longest = Math.max(...stages.map((stage) => stage.ms), 1);

  return (
    <div className="space-y-1">
      {stages.map((stage) => (
        <div key={stage.key} className="flex items-center gap-2 text-[11px]">
          <span className="w-16 shrink-0 text-right font-mono text-muted-foreground">
            {stage.ms} ms
          </span>
          <span className="flex h-2 min-w-0 flex-1 items-center">
            <span
              className="h-2 rounded-sm"
              style={{
                width: `${Math.max(2, (stage.ms / longest) * 100)}%`,
                // Stages a node owns are the ones you can change by editing a box;
                // the rest are settings, and worth telling apart at a glance.
                background: stage.node_id ? "var(--primary)" : "var(--muted-foreground)",
              }}
            />
          </span>
          <span className="w-64 shrink-0 truncate text-muted-foreground">
            {stage.label}
            <span className="ml-1 opacity-60">[{stage.node_id ?? stage.owner}]</span>
            {throughputLabel(stage) ? (
              <span className="ml-1.5 font-mono text-foreground/70">{throughputLabel(stage)}</span>
            ) : null}
          </span>
        </div>
      ))}
    </div>
  );
}
