import { AgentEditor } from "@/components/canvas/agent-editor";
import { RuntimeDown } from "@/components/runtime-down";
import { emptyConfig } from "@/lib/agent/config";
import { api, apiReachable } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Page() {
  if (!(await apiReachable())) return <RuntimeDown />;

  const providers = await api.providers();
  return <AgentEditor providers={providers} config={emptyConfig()} />;
}
