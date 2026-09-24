"use client";

import { Phone, TriangleAlert } from "lucide-react";
import { useEffect, useRef } from "react";

import { useCallState } from "@/components/canvas/call-context";

const BAR_WIDTH = 120;

export function CallPanel() {
  const call = useCallState();
  const transcriptEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    transcriptEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [call?.transcript.length]);

  if (!call || call.status === "idle") return null;

  const lastTurn = call.turns[call.turns.length - 1];
  const totals = call.turns.map((turn) => turn.total_ms);
  const median = totals.length
    ? [...totals].sort((a, b) => a - b)[Math.floor((totals.length - 1) / 2)]
    : 0;

  return (
    <section className="flex h-56 shrink-0 border-t border-border bg-sidebar">
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b border-border px-4 py-2 text-xs">
          <Phone className="size-3.5 text-primary" />
          <span className="font-medium">Transcript</span>
          {call.status === "failed" ? (
            <span className="flex items-center gap-1 text-destructive">
              <TriangleAlert className="size-3" />
              {call.detail ?? "call failed"}
            </span>
          ) : (
            <span className="text-muted-foreground">
              {call.status === "connecting" ? "connecting…" : `${call.turns.length} turns`}
            </span>
          )}
        </header>

        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto px-4 py-3">
          {call.transcript.map((line, index) => (
            <div key={index} className="flex gap-2 text-sm">
              <span
                className={
                  line.role === "user"
                    ? "shrink-0 text-muted-foreground"
                    : "shrink-0 font-medium text-primary"
                }
              >
                {line.role === "user" ? "you" : "agent"}
              </span>
              <span className="min-w-0">
                {line.text}
                {line.interrupted ? (
                  <span className="ml-1 text-[11px] text-muted-foreground">[interrupted]</span>
                ) : null}
              </span>
            </div>
          ))}
          {call.transcript.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {call.status === "live" ? "Say something." : "Waiting for the agent…"}
            </p>
          ) : null}
          <div ref={transcriptEnd} />
        </div>
      </div>

      <div className="w-96 shrink-0 border-l border-border">
        <header className="flex items-baseline gap-2 border-b border-border px-4 py-2 text-xs">
          <span className="font-medium">Last turn</span>
          {lastTurn ? (
            <>
              <span className="font-mono text-foreground">{lastTurn.total_ms} ms</span>
              <span className="text-muted-foreground">to first audio</span>
              <span className="ml-auto text-muted-foreground">median {median} ms</span>
            </>
          ) : (
            <span className="text-muted-foreground">waiting for a turn</span>
          )}
        </header>

        <div className="space-y-1 overflow-y-auto px-4 py-3" style={{ maxHeight: "11rem" }}>
          {lastTurn?.stages.map((stage) => {
            const longest = Math.max(...lastTurn.stages.map((s) => s.ms), 1);
            return (
              <div key={stage.key} className="flex items-center gap-2 text-[11px]">
                <span className="w-14 shrink-0 text-right font-mono text-muted-foreground">
                  {stage.ms} ms
                </span>
                <span
                  className="h-2 shrink-0 rounded-sm"
                  style={{
                    width: `${Math.max(3, (stage.ms / longest) * BAR_WIDTH)}px`,
                    background: stage.node_id ? "var(--primary)" : "var(--muted-foreground)",
                  }}
                />
                <span className="min-w-0 truncate text-muted-foreground">
                  {stage.label}
                  <span className="ml-1 opacity-60">[{stage.node_id ?? stage.owner}]</span>
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
