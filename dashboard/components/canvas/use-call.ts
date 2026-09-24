"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Call, type CallStatus, type TranscriptLine, type TurnEvent } from "@/lib/call";
import type { AgentConfig } from "@/lib/schema/agent.gen";

export type CallState = {
  status: CallStatus;
  detail?: string;
  transcript: TranscriptLine[];
  turns: TurnEvent[];
  /** Latency per node from the most recent turn, for the badges on the canvas. */
  byNode: Record<string, number>;
  start: (config: AgentConfig, slug?: string) => void;
  stop: () => void;
};

export function useCall(): CallState {
  const [status, setStatus] = useState<CallStatus>("idle");
  const [detail, setDetail] = useState<string>();
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [turns, setTurns] = useState<TurnEvent[]>([]);
  const call = useRef<Call | null>(null);

  const handlers = useMemo(
    () => ({
      onStatus: (next: CallStatus, why?: string) => {
        setStatus(next);
        setDetail(why);
      },
      onTranscript: (line: TranscriptLine) => setTranscript((lines) => [...lines, line]),
      onTurn: (turn: TurnEvent) => setTurns((all) => [...all, turn]),
    }),
    [],
  );

  const start = useCallback(
    (config: AgentConfig, slug?: string) => {
      setTranscript([]);
      setTurns([]);
      setDetail(undefined);
      call.current = new Call(handlers);
      void call.current.start(config, slug);
    },
    [handlers],
  );

  const stop = useCallback(() => {
    void call.current?.stop();
    call.current = null;
  }, []);

  // Hanging up when the page goes away matters: the runtime would otherwise keep
  // the pipeline (and the provider connections) running.
  useEffect(() => () => void call.current?.stop(), []);

  const byNode = turns.length ? turns[turns.length - 1].by_node : {};

  return { status, detail, transcript, turns, byNode, start, stop };
}
