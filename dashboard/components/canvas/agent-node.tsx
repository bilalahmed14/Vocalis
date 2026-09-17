"use client";

import { Handle, type NodeProps, Position } from "@xyflow/react";

import type { AgentNode as AgentNodeType } from "@/lib/agent/flow";
import { PORTS, type PortType } from "@/lib/schema/ports";
import { cn } from "@/lib/utils";
import { useProviders } from "@/components/canvas/providers-context";

const PORT_STYLE: Record<PortType, string> = {
  audio: "!bg-sky-500 !border-sky-300",
  text: "!bg-violet-500 !border-violet-300",
};

export function AgentNode({ id, data, selected }: NodeProps<AgentNodeType>) {
  const provider = useProviders().find((p) => p.type === data.type && p.id === data.provider);
  const ports = PORTS[data.type];
  const summary = Object.entries(data.params)
    .filter(([, value]) => value !== "" && value !== undefined)
    .slice(0, 2)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : String(value)}`);

  return (
    <div
      className={cn(
        "w-56 rounded-lg border bg-card text-card-foreground shadow-sm transition-colors",
        selected ? "border-primary ring-1 ring-primary" : "border-border",
      )}
    >
      <Handle
        type="target"
        position={Position.Left}
        className={cn("!h-3 !w-3 !border-2", PORT_STYLE[ports.input])}
        title={`${ports.input} in`}
      />

      <div className="flex items-center gap-2 border-b px-3 py-2">
        {provider?.icon ? (
          <span className="size-5 shrink-0" dangerouslySetInnerHTML={{ __html: provider.icon }} />
        ) : (
          <span className="size-5 shrink-0 rounded bg-muted" />
        )}
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium">{data.label || provider?.name || data.provider}</div>
          <div className="truncate text-xs text-muted-foreground">{id}</div>
        </div>
        <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          {data.type}
        </span>
      </div>

      <div className="space-y-0.5 px-3 py-2 text-xs text-muted-foreground">
        {summary.length > 0 ? (
          summary.map((line) => (
            <div key={line} className="truncate">
              {line}
            </div>
          ))
        ) : (
          <div className="italic">defaults</div>
        )}
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className={cn("!h-3 !w-3 !border-2", PORT_STYLE[ports.output])}
        title={`${ports.output} out`}
      />
    </div>
  );
}
