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

/** A module in a rack: silkscreened stage, a signal lamp, and jacks on both sides. */
export function AgentNode({ id, data, selected }: NodeProps<AgentNodeType>) {
  const provider = useProviders().find((p) => p.type === data.type && p.id === data.provider);
  const call = useCallState();
  const latencyMs = call?.byNode[id];
  const live = call?.status === "live";

  const stage = STAGE[data.type];
  const ports = PORTS[data.type];
  const settings = Object.entries(data.params)
    .filter(([, value]) => value !== "" && value !== undefined && !(Array.isArray(value) && !value.length))
    .slice(0, 3);

  return (
    <div
      className={cn(
        "w-60 rounded-md border bg-card transition-colors",
        selected ? "border-primary" : "border-border hover:border-muted-foreground/40",
      )}
      style={selected ? { boxShadow: `0 0 0 1px ${stage.color}` } : undefined}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!size-3 !border-2 !border-background"
        style={{ background: PORT_COLOR[ports.input], boxShadow: `0 0 0 1px ${PORT_COLOR[ports.input]}55` }}
        title={`${ports.input} in`}
      />

      <div className="flex items-center gap-2 border-b border-border/70 px-2.5 py-1.5">
        <span
          className={cn("size-1.5 shrink-0 rounded-full", live && latencyMs ? "signal-live" : "")}
          style={{ background: live && latencyMs ? stage.color : "var(--muted-foreground)" }}
          title={live ? "carrying signal" : "idle"}
        />
        <span className="silkscreen" style={{ color: stage.color }}>
          {stage.short}
        </span>
        <span className="readout ml-auto truncate text-[10px] text-muted-foreground">{id}</span>
      </div>

      <div className="flex items-center gap-2.5 px-2.5 py-2.5">
        {provider?.icon ? (
          <span
            className="flex size-7 shrink-0 items-center justify-center overflow-hidden rounded [&>svg]:size-7"
            dangerouslySetInnerHTML={{ __html: provider.icon }}
          />
        ) : (
          <span className="size-7 shrink-0 rounded bg-muted" />
        )}
        <span className="min-w-0 flex-1 truncate text-sm">
          {data.label || provider?.name || data.provider}
        </span>

        {latencyMs !== undefined ? (
          <span className="readout shrink-0 text-xs" style={{ color: stage.color }}>
            {latencyMs}
            <span className="ml-0.5 text-[10px] text-muted-foreground">ms</span>
          </span>
        ) : provider === undefined ? (
          <TriangleAlert className="size-4 shrink-0 text-destructive" />
        ) : provider.env?.length ? (
          <KeyRound className="size-3 shrink-0 text-muted-foreground/60" />
        ) : null}
      </div>

      {settings.length ? (
        <dl className="space-y-0.5 border-t border-border/70 px-2.5 py-2">
          {settings.map(([key, value]) => (
            <div key={key} className="flex items-baseline gap-2 text-[11px]">
              <dt className="shrink-0 text-muted-foreground">{key}</dt>
              <dd className="readout ml-auto min-w-0 truncate text-foreground/80">
                {Array.isArray(value) ? value.join(", ") : String(value)}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}

      <Handle
        type="source"
        position={Position.Right}
        className="!size-3 !border-2 !border-background"
        style={{ background: PORT_COLOR[ports.output], boxShadow: `0 0 0 1px ${PORT_COLOR[ports.output]}55` }}
        title={`${ports.output} out`}
      />
    </div>
  );
}
