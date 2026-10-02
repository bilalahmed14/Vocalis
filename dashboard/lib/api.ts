/**
 * Talking to the Vocalis runtime API.
 *
 * Server components call the runtime directly (VOCALIS_API_URL, which in Docker is
 * the `api` service); the browser goes through this app's /api proxy, so there is no
 * CORS setup and no public API URL to configure.
 */
import type { AgentConfig } from "@/lib/schema/agent.gen";
import type { ProviderManifest } from "@/lib/schema/provider.gen";
import type { NodeType } from "@/lib/schema/ports";

export type Provider = ProviderManifest & { type: NodeType; icon: string | null };

export type SavedAgent = {
  name: string;
  slug: string;
  version: number;
  config: AgentConfig;
  updated_at: string;
};

export type AgentSummary = Omit<SavedAgent, "config">;

export type AgentVersion = { version: number; note: string | null; created_at: string };

export type CallLog = {
  id: string;
  agent_name: string;
  agent_slug: string | null;
  agent_version: number | null;
  started_at: string;
  ended_at: string | null;
  turn_count: number;
  interrupted_turns: number;
  p50_ms: number | null;
  p95_ms: number | null;
};

export type CallStage = {
  key: string;
  label: string;
  owner: string;
  node_id: string | null;
  ms: number;
  /** What the model produced in that time, when the service reports it. */
  tokens_per_sec?: number;
  chars_per_sec?: number;
  realtime_factor?: number;
};

export type CallLogDetail = {
  call: CallLog;
  config: AgentConfig;
  turns: { turn: number; total_ms: number; interrupted: boolean; stages: CallStage[]; at: string }[];
  messages: { role: "user" | "agent"; text: string; interrupted: boolean; at: string }[];
};

export type AgentCallStats = { calls: number; turns: number; median_ms: number | null };

export type Overview = {
  agents: number;
  calls: number;
  turns: number;
  p50_ms: number | null;
  p95_ms: number | null;
  interrupted_share: number;
  daily: { day: string; calls: number; p50_ms: number | null }[];
  slowest_stages: { label: string; node_id: string | null; median_ms: number }[];
  recent: CallLog[];
};

export type Template = {
  id: string;
  name: string;
  description: string;
  needs_keys: string[];
  config: AgentConfig;
};

export type ApiIssue = {
  message: string;
  node_id: string | null;
  node_index: number | null;
  edge_index: number | null;
  path: string;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly issues: ApiIssue[] = [],
  ) {
    super(message);
  }
}

function baseUrl(): string {
  return typeof window === "undefined"
    ? (process.env.VOCALIS_API_URL ?? "http://localhost:8000")
    : "/api";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl()}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "content-type": "application/json", ...init?.headers },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const issues: ApiIssue[] = body?.detail?.issues ?? [];
    const message =
      issues.map((issue) => issue.message).join("; ") ||
      (typeof body?.detail === "string" ? body.detail : `request failed (${response.status})`);
    throw new ApiError(message, response.status, issues);
  }

  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export const api = {
  providers: () => request<Provider[]>("/providers"),
  agents: () => request<AgentSummary[]>("/agents"),
  agent: (slug: string) => request<SavedAgent>(`/agents/${slug}`),
  versions: (slug: string) => request<AgentVersion[]>(`/agents/${slug}/versions`),
  versionConfig: (slug: string, version: number) =>
    request<SavedAgent>(`/agents/${slug}/versions/${version}`),

  create: (config: AgentConfig, note?: string) =>
    request<SavedAgent>("/agents", { method: "POST", body: JSON.stringify({ config, note }) }),
  save: (slug: string, config: AgentConfig, note?: string) =>
    request<SavedAgent>(`/agents/${slug}`, { method: "PUT", body: JSON.stringify({ config, note }) }),
  restore: (slug: string, version: number) =>
    request<SavedAgent>(`/agents/${slug}/versions/${version}/restore`, { method: "POST" }),
  remove: (slug: string) => request<void>(`/agents/${slug}`, { method: "DELETE" }),

  templates: () => request<Template[]>("/templates"),
  logs: (agent?: string, limit = 50) =>
    request<CallLog[]>(`/logs?limit=${limit}${agent ? `&agent=${encodeURIComponent(agent)}` : ""}`),
  log: (id: string) => request<CallLogDetail>(`/logs/${encodeURIComponent(id)}`),
  deleteLog: (id: string) => request<void>(`/logs/${encodeURIComponent(id)}`, { method: "DELETE" }),
  callStats: (slug: string) => request<AgentCallStats>(`/agents/${slug}/calls`),
  overview: (days = 14) => request<Overview>(`/stats?days=${days}`),
};

/** Is the runtime up? Used to show a helpful message instead of a crash. */
export async function apiReachable(): Promise<boolean> {
  try {
    await request<{ status: string }>("/healthz");
    return true;
  } catch {
    return false;
  }
}
