"use client";

import { createContext, useContext } from "react";

import type { Provider } from "@/lib/providers";

const ProvidersContext = createContext<Provider[]>([]);

export function ProvidersProvider({ value, children }: { value: Provider[]; children: React.ReactNode }) {
  return <ProvidersContext.Provider value={value}>{children}</ProvidersContext.Provider>;
}

export function useProviders(): Provider[] {
  return useContext(ProvidersContext);
}
