import { CallTable } from "@/components/calls/call-table";
import { RuntimeDown } from "@/components/runtime-down";
import { PageHeader } from "@/components/shell/page-header";
import { api, apiReachable } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Page() {
  if (!(await apiReachable())) return <RuntimeDown />;

  const calls = await api.logs();

  return (
    <>
      <PageHeader title="Calls" subtitle="Every test call, with where its time went." />
      <div className="min-h-0 flex-1 overflow-y-auto px-8 py-6">
        <div className="mx-auto max-w-5xl">
          <CallTable calls={calls} />
        </div>
      </div>
    </>
  );
}
