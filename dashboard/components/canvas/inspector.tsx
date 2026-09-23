"use client";

import { ExternalLink, KeyRound, MousePointerClick, Trash2, TriangleAlert } from "lucide-react";

import { ParamsForm } from "@/components/canvas/params-form";
import { useProviders } from "@/components/canvas/providers-context";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { AgentNode, NodeData } from "@/lib/agent/flow";
import { STAGE } from "@/lib/schema/stages";

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
      <aside className="flex w-80 shrink-0 flex-col items-center justify-center gap-3 border-l border-border bg-sidebar px-8 text-center">
        <span className="flex size-10 items-center justify-center rounded-xl bg-muted text-muted-foreground">
          <MousePointerClick className="size-5" />
        </span>
        <p className="text-sm text-muted-foreground">
          Select a node to change its provider and settings.
        </p>
      </aside>
    );
  }

  const stage = STAGE[node.data.type];
  const provider = providers.find((p) => p.type === node.data.type && p.id === node.data.provider);
  const params = (provider?.params ?? {}) as {
    properties?: Record<string, never>;
    required?: string[];
  };

  return (
    <aside className="flex w-80 shrink-0 flex-col overflow-y-auto border-l border-border bg-sidebar">
      <div className="flex items-start gap-3 border-b border-border px-4 py-3.5">
        {provider?.icon ? (
          <span
            className="flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-lg [&>svg]:size-8"
            dangerouslySetInnerHTML={{ __html: provider.icon }}
          />
        ) : (
          <span className="size-8 shrink-0 rounded-lg bg-muted" />
        )}
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium">{provider?.name ?? node.data.provider}</div>
          <div className="text-[11px]" style={{ color: stage.color }}>
            {stage.label}
          </div>
        </div>
        <button
          type="button"
          onClick={onDelete}
          title="Delete node"
          className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
        >
          <Trash2 className="size-4" />
        </button>
      </div>

      {issues.length ? (
        <ul className="space-y-1 border-b border-destructive/20 bg-destructive/5 px-4 py-3 text-xs text-destructive">
          {issues.map((issue) => (
            <li key={issue} className="flex gap-1.5">
              <TriangleAlert className="mt-0.5 size-3 shrink-0" />
              <span>{issue}</span>
            </li>
          ))}
        </ul>
      ) : null}

      <div className="space-y-4 px-4 py-4">
        <Field label="Provider">
          <select
            value={node.data.provider}
            onChange={(event) => onChange({ provider: event.target.value, params: {} })}
            className="h-9 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus:border-ring"
          >
            {providers
              .filter((candidate) => candidate.type === node.data.type)
              .map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.name}
                </option>
              ))}
          </select>
          <div className="flex items-center justify-between gap-2">
            {provider?.env?.length ? (
              <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                <KeyRound className="size-3" />
                {provider.env.join(", ")}
              </span>
            ) : (
              <span className="text-[11px] text-muted-foreground">Runs locally, no key</span>
            )}
            {provider?.docs_url ? (
              <a
                href={provider.docs_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
              >
                Docs <ExternalLink className="size-3" />
              </a>
            ) : null}
          </div>
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Node id">
            <Input
              className="h-9 font-mono text-xs"
              value={node.id}
              onChange={(event) => onRename(event.target.value)}
            />
          </Field>
          <Field label="Label">
            <Input
              className="h-9"
              placeholder={provider?.name ?? ""}
              value={node.data.label ?? ""}
              onChange={(event) => onChange({ label: event.target.value || undefined })}
            />
          </Field>
        </div>

        {node.data.type === "llm" ? (
          <Field label="System prompt" required>
            <Textarea
              rows={7}
              className="resize-y text-sm"
              placeholder="You are a friendly voice assistant…"
              value={node.data.system_prompt ?? ""}
              onChange={(event) => onChange({ system_prompt: event.target.value })}
            />
            <p className="text-[11px] text-muted-foreground">
              Spoken aloud, so ask for short replies and no markdown.
            </p>
          </Field>
        ) : null}
      </div>

      {params.properties && Object.keys(params.properties).length ? (
        <div className="border-t border-border px-4 py-4">
          <h3 className="mb-3 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            {provider?.name} settings
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

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">
        {label}
        {required ? <span className="text-destructive"> *</span> : null}
      </Label>
      {children}
    </div>
  );
}
