import { NewAgent } from "@/components/agents/new-agent";
import { RuntimeDown } from "@/components/runtime-down";
import { api, apiReachable } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Page() {
  if (!(await apiReachable())) return <RuntimeDown />;

  const templates = await api.templates();
  return <NewAgent templates={templates} />;
}
