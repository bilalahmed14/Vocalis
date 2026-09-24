"use client";

import {
  CircleCheck,
  Download,
  History,
  Phone,
  PhoneOff,
  Save,
  TriangleAlert,
  Upload,
} from "lucide-react";
import Link from "next/link";
import { useRef } from "react";

import { Button } from "@/components/ui/button";
import type { AgentVersion } from "@/lib/api";
import { cn } from "@/lib/utils";

export type SaveState = { kind: "idle" | "saving" | "saved" | "error"; message?: string };

export function Toolbar({
  name,
  onNameChange,
  issueCount,
  saved,
  versions,
  state,
  onSave,
  onImport,
  onExport,
  onOpenVersion,
  onRestore,
  call,
}: {
  name: string;
  onNameChange: (name: string) => void;
  issueCount: number;
  saved: { slug: string; version: number } | null;
  versions: AgentVersion[];
  state: SaveState;
  onSave: () => void;
  onImport: (file: File) => void;
  onExport: () => void;
  onOpenVersion: (version: number) => void;
  onRestore: (version: number) => void;
  call: { status: string; onStart: () => void; onStop: () => void };
}) {
  const fileInput = useRef<HTMLInputElement>(null);
  const latest = versions[0]?.version;
  const viewingOld = saved != null && latest != null && saved.version !== latest;

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border px-4">
      <div className="flex min-w-0 items-center gap-2 text-sm">
        <Link href="/" className="shrink-0 text-muted-foreground hover:text-foreground">
          Agents
        </Link>
        <span className="text-muted-foreground/50">/</span>
        <input
          aria-label="Agent name"
          value={name}
          onChange={(event) => onNameChange(event.target.value)}
          className="w-52 rounded-md border border-transparent bg-transparent px-1.5 py-1 font-medium outline-none hover:border-border focus:border-ring"
        />
      </div>

      <span
        className={cn(
          "flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
          issueCount
            ? "bg-destructive/10 text-destructive"
            : "bg-success/10 text-success",
        )}
      >
        {issueCount ? <TriangleAlert className="size-3" /> : <CircleCheck className="size-3" />}
        {issueCount ? `${issueCount} problem${issueCount > 1 ? "s" : ""}` : "Ready"}
      </span>

      {saved && versions.length > 0 ? (
        <div className="flex shrink-0 items-center gap-1.5">
          <History className="size-3.5 text-muted-foreground" />
          <select
            aria-label="Version history"
            value={saved.version}
            onChange={(event) => onOpenVersion(Number(event.target.value))}
            className="h-7 max-w-44 rounded-md border border-input bg-background px-1.5 text-xs outline-none focus:border-ring"
          >
            {versions.map((version) => (
              <option key={version.version} value={version.version}>
                v{version.version}
                {version.note ? ` — ${version.note}` : ""}
              </option>
            ))}
          </select>
          {viewingOld ? (
            <Button size="sm" variant="outline" className="h-7" onClick={() => onRestore(saved.version)}>
              Restore
            </Button>
          ) : null}
        </div>
      ) : null}

      {state.message ? (
        <span
          className={cn(
            "min-w-0 truncate text-xs",
            state.kind === "error" ? "text-destructive" : "text-muted-foreground",
          )}
          title={state.message}
        >
          {state.message}
        </span>
      ) : null}

      <div className="ml-auto flex shrink-0 items-center gap-1.5">
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
        <Button variant="ghost" size="sm" onClick={() => fileInput.current?.click()} title="Import JSON">
          <Upload className="size-4" />
        </Button>
        <Button variant="ghost" size="sm" onClick={onExport} title="Export JSON">
          <Download className="size-4" />
        </Button>
        <Button variant="outline" size="sm" onClick={onSave} disabled={state.kind === "saving"}>
          <Save className="size-4" />
          {state.kind === "saving" ? "Saving…" : saved ? "Save version" : "Save"}
        </Button>
        {call.status === "live" || call.status === "connecting" ? (
          <Button size="sm" variant="destructive" onClick={call.onStop} className="gap-1.5">
            <PhoneOff className="size-4" />
            {call.status === "connecting" ? "Connecting…" : "End call"}
          </Button>
        ) : (
          <Button
            size="sm"
            onClick={call.onStart}
            disabled={issueCount > 0}
            title={issueCount > 0 ? "Fix the problems first" : "Call this agent from your browser"}
            className="gap-1.5"
          >
            <Phone className="size-4" />
            Test call
          </Button>
        )}
      </div>
    </header>
  );
}
