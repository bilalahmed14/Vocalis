"use client";

import Link from "next/link";
import { useRef } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { AgentSummary, AgentVersion } from "@/lib/api";

export type SaveState = { kind: "idle" | "saving" | "saved" | "error"; message?: string };

export function Toolbar({
  name,
  onNameChange,
  issueCount,
  agents,
  saved,
  versions,
  state,
  onSave,
  onImport,
  onExport,
  onOpenVersion,
  onRestore,
}: {
  name: string;
  onNameChange: (name: string) => void;
  issueCount: number;
  agents: AgentSummary[];
  saved: { slug: string; version: number } | null;
  versions: AgentVersion[];
  state: SaveState;
  onSave: () => void;
  onImport: (file: File) => void;
  onExport: () => void;
  onOpenVersion: (version: number) => void;
  onRestore: (version: number) => void;
}) {
  const fileInput = useRef<HTMLInputElement>(null);

  return (
    <header className="flex flex-wrap items-center gap-3 border-b px-4 py-2">
      <Link href="/" className="font-semibold">
        Vocalis
      </Link>

      <select
        aria-label="Open an agent"
        className="h-8 max-w-40 rounded-md border bg-transparent px-2 text-sm"
        value={saved?.slug ?? ""}
        onChange={(event) => {
          window.location.href = event.target.value ? `/agents/${event.target.value}` : "/new";
        }}
      >
        <option value="">New agent</option>
        {agents.map((agent) => (
          <option key={agent.slug} value={agent.slug}>
            {agent.name}
          </option>
        ))}
      </select>

      <Input
        aria-label="Agent name"
        className="h-8 w-56"
        value={name}
        onChange={(event) => onNameChange(event.target.value)}
      />

      <span
        className={
          issueCount
            ? "rounded bg-destructive/10 px-2 py-1 text-xs text-destructive"
            : "rounded bg-emerald-500/10 px-2 py-1 text-xs text-emerald-600"
        }
      >
        {issueCount ? `${issueCount} problem${issueCount > 1 ? "s" : ""}` : "valid"}
      </span>

      {saved && versions.length > 0 ? (
        <select
          aria-label="Version history"
          className="h-8 rounded-md border bg-transparent px-2 text-sm"
          value={saved.version}
          onChange={(event) => onOpenVersion(Number(event.target.value))}
        >
          {versions.map((version) => (
            <option key={version.version} value={version.version}>
              v{version.version}
              {version.note ? ` — ${version.note}` : ""}
            </option>
          ))}
        </select>
      ) : null}

      {saved && saved.version !== versions[0]?.version ? (
        <Button variant="outline" size="sm" onClick={() => onRestore(saved.version)}>
          Restore v{saved.version}
        </Button>
      ) : null}

      <span
        className={`text-xs ${state.kind === "error" ? "text-destructive" : "text-muted-foreground"}`}
      >
        {state.message}
      </span>

      <div className="ml-auto flex gap-2">
        <input
          ref={fileInput}
          type="file"
          accept="application/json"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) onImport(file);
            event.target.value = "";
          }}
        />
        <Button variant="ghost" size="sm" onClick={() => fileInput.current?.click()}>
          Import
        </Button>
        <Button variant="outline" size="sm" onClick={onExport}>
          Export JSON
        </Button>
        <Button size="sm" onClick={onSave} disabled={state.kind === "saving"}>
          {state.kind === "saving" ? "Saving…" : saved ? "Save version" : "Save"}
        </Button>
      </div>
    </header>
  );
}
