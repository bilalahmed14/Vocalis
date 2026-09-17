import { readFile } from "node:fs/promises";
import path from "node:path";

import { AgentEditor } from "@/components/canvas/agent-editor";
import { loadProviders } from "@/lib/providers";
import { emptyConfig } from "@/lib/agent/config";
import type { AgentConfig } from "@/lib/schema/agent.gen";

export const dynamic = "force-dynamic";

async function startingAgent(): Promise<AgentConfig> {
  const example = path.join(process.cwd(), "..", "examples", "basic.json");
  return readFile(example, "utf8")
    .then((text) => JSON.parse(text) as AgentConfig)
    .catch(() => emptyConfig());
}

export default async function Page() {
  const [providers, config] = await Promise.all([loadProviders(), startingAgent()]);
  return <AgentEditor providers={providers} config={config} />;
}
