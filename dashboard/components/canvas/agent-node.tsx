"use client";

import { Handle, type NodeProps, Position } from "@xyflow/react";
import { KeyRound, TriangleAlert } from "lucide-react";

import { useCallState } from "@/components/canvas/call-context";
import { useProviders } from "@/components/canvas/providers-context";
import type { AgentNode as AgentNodeType } from "@/lib/agent/flow";
import { PORTS, type PortType } from "@/lib/schema/ports";
import { STAGE } from "@/lib/schema/stages";
import { cn } from "@/lib/utils";

const PORT_COLOR: Record<PortType, string> = {
  audio: "var(--port-audio)",
  text: "var(--port-text)",
};

export function AgentNode({ id, data, selected }: NodeProps<AgentNodeType>) {
  const provider = useProviders().find((p) => p.type === data.type && p.id === data.provider);
  const call = useCallState();
  const latencyMs = call?.byNode[id];
  const stage = STAGE[data.type];
  const ports = PORTS[data.type];

  const settings = Object.entries(data.params)
    .filter(([, value]) => value !== "" && value !== undefined && !(Array.isArray(value) && !value.length))
    .slice(0, 3);

  return (
    <div
      className={cn(
        "w-60 overflow-hidden rounded-xl border bg-card shadow-lg transition-all",
        selected ? "border-primary shadow-primary/20" : "border-border hover:border-border/80",
      )}
      style={selected ? { boxShadow: `0 0 0 1px ${stage.color}55, 0 8px 30px -12px ${stage.color}` } : undefined}
    >
      {/* Stage stripe: the colour is how you tell the four stages apart at a glance. */}
      <div className="h-0.5 w-full" style={{ background: stage.color }} />

      <Handle
        type="target"
        position={Position.Left}
        className="!size-2.5 !border-2 !border-background"
        style={{ background: PORT_COLOR[ports.input] }}
        title={`${ports.input} in`}
      />

      <div className="flex items-center gap-2.5 px-3 py-2.5">
        {provider?.icon ? (
          <span
            className="flex size-7 shrink-0 items-center justify-center overflow-hidden rounded-md [&>svg]:size-7"
            dangerouslySetInnerHTML={{ __html: provider.icon }}
          />
        ) : (
          <span className="size-7 shrink-0 rounded-md bg-muted" />
        )}

        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium leading-tight">
            {data.label || provider?.name || data.provider}
          </div>
          <div className="mt-0.5 flex items-center gap-1.5">
            <span
              className="text-[10px] font-semibold uppercase tracking-wider"
              style={{ color: stage.color }}
            >
              {stage.short}
            </span>
            <span className="truncate font-mono text-[10px] text-muted-foreground">{id}</span>
          </div>
        </div>

        {latencyMs !== undefined ? (
          // What this node cost on the last turn of the live call.
          <span
            className="shrink-0 rounded-md px-1.5 py-0.5 font-mono text-[10px] font-medium"
            style={{ background: `${stage.color}22`, color: stage.color }}
            title="last turn"
          >
            {latencyMs} ms
          </span>
        ) : provider === undefined ? (
          <TriangleAlert className="size-4 shrink-0 text-destructive" />
        ) : provider.env?.length ? (
          <KeyRound className="size-3.5 shrink-0 text-muted-foreground/70" />
        ) : null}
      </div>

      {settings.length ? (
        <div className="space-y-1 border-t border-border/60 bg-surface/60 px-3 py-2">
          {settings.map(([key, value]) => (
            <div key={key} className="flex items-baseline gap-2 text-[11px]">
              <span className="shrink-0 text-muted-foreground">{key}</span>
              <span className="truncate font-mono text-foreground/90">
                {Array.isArray(value) ? value.join(", ") : String(value)}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div className="border-t border-border/60 bg-surface/60 px-3 py-2 text-[11px] italic text-muted-foreground">
          provider defaults
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="!size-2.5 !border-2 !border-background"
        style={{ background: PORT_COLOR[ports.output] }}
        title={`${ports.output} out`}
      />
    </div>
  );
}
