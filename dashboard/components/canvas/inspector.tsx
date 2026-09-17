"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ParamsForm } from "@/components/canvas/params-form";
import { useProviders } from "@/components/canvas/providers-context";
import type { AgentNode, NodeData } from "@/lib/agent/flow";

export function Inspector({
  node,
  issues,
  onChange,
  onRename,
  onDelete,
}: {
  node: AgentNode | null;
  issues: string[];
  onChange: (data: Partial<NodeData>) => void;
  onRename: (id: string) => void;
  onDelete: () => void;
}) {
  const providers = useProviders();

  if (!node) {
    return (
      <aside className="w-80 shrink-0 border-l bg-background p-4">
        <p className="text-sm text-muted-foreground">Select a node to edit it.</p>
      </aside>
    );
  }

  const provider = providers.find((p) => p.type === node.data.type && p.id === node.data.provider);
  const params = (provider?.params ?? {}) as {
    properties?: Record<string, never>;
    required?: string[];
  };

  return (
    <aside className="flex w-80 shrink-0 flex-col gap-4 overflow-y-auto border-l bg-background p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold">{provider?.name ?? node.data.provider}</h2>
          <p className="text-xs text-muted-foreground">{node.data.type} node</p>
        </div>
        <button
          type="button"
          onClick={onDelete}
          className="rounded border px-2 py-1 text-xs text-muted-foreground hover:border-destructive hover:text-destructive"
        >
          Delete
        </button>
      </div>

      {issues.length > 0 ? (
        <ul className="space-y-1 rounded-md border border-destructive/40 bg-destructive/5 p-2 text-xs text-destructive">
          {issues.map((issue) => (
            <li key={issue}>{issue}</li>
          ))}
        </ul>
      ) : null}

      <div className="space-y-1">
        <Label htmlFor="node-id" className="text-xs">
          Node id
        </Label>
        <Input
          id="node-id"
          className="h-8 font-mono text-xs"
          value={node.id}
          onChange={(event) => onRename(event.target.value)}
        />
      </div>

      <div className="space-y-1">
        <Label htmlFor="node-provider" className="text-xs">
          Provider
        </Label>
        <select
          id="node-provider"
          className="h-8 w-full rounded-md border bg-transparent px-2 text-sm"
          value={node.data.provider}
          onChange={(event) => onChange({ provider: event.target.value, params: {} })}
        >
          {providers
            .filter((candidate) => candidate.type === node.data.type)
            .map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                {candidate.name}
              </option>
            ))}
        </select>
        {provider?.env && provider.env.length > 0 ? (
          <p className="text-[11px] text-muted-foreground">Needs {provider.env.join(", ")} in .env</p>
        ) : null}
      </div>

      <div className="space-y-1">
        <Label htmlFor="node-label" className="text-xs">
          Label
        </Label>
        <Input
          id="node-label"
          className="h-8"
          placeholder={provider?.name ?? ""}
          value={node.data.label ?? ""}
          onChange={(event) => onChange({ label: event.target.value || undefined })}
        />
      </div>

      {node.data.type === "llm" ? (
        <div className="space-y-1">
          <Label htmlFor="system-prompt" className="text-xs">
            System prompt <span className="text-destructive">*</span>
          </Label>
          <Textarea
            id="system-prompt"
            rows={6}
            value={node.data.system_prompt ?? ""}
            onChange={(event) => onChange({ system_prompt: event.target.value })}
          />
        </div>
      ) : null}

      {params.properties ? (
        <div className="space-y-2 border-t pt-3">
          <h3 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Settings
          </h3>
          <ParamsForm
            schema={params.properties}
            required={params.required ?? []}
            values={node.data.params}
            onChange={(next) => onChange({ params: next })}
          />
        </div>
      ) : null}
    </aside>
  );
}
