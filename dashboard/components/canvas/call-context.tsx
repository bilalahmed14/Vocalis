"use client";

import { createContext, useContext } from "react";

import type { CallState } from "@/components/canvas/use-call";

const CallContext = createContext<CallState | null>(null);

export function CallProvider({ value, children }: { value: CallState; children: React.ReactNode }) {
  return <CallContext.Provider value={value}>{children}</CallContext.Provider>;
}

/** The live call, if the canvas is inside one. */
export function useCallState(): CallState | null {
  return useContext(CallContext);
}
