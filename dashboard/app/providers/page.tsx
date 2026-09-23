import { Check, ExternalLink, KeyRound } from "lucide-react";

import { RuntimeDown } from "@/components/runtime-down";
import { PageHeader } from "@/components/shell/page-header";
import { api, apiReachable } from "@/lib/api";
import { NODE_TYPES } from "@/lib/schema/ports";
import { STAGE } from "@/lib/schema/stages";

export const dynamic = "force-dynamic";

export default async function Page() {
  if (!(await apiReachable())) return <RuntimeDown />;

  const providers = await api.providers();

  return (
    <>
      <PageHeader
        title="Providers"
        subtitle="Plugins the runtime found. Drop a folder in /providers to add one."
      />

      <div className="min-h-0 flex-1 overflow-y-auto px-8 py-6">
        <div className="mx-auto max-w-4xl space-y-8">
          {NODE_TYPES.map((type) => {
            const stage = STAGE[type];
            const items = providers.filter((provider) => provider.type === type);

            return (
              <section key={type}>
                <div className="mb-3 flex items-baseline gap-2">
                  <span className="size-2 rounded-full" style={{ background: stage.color }} />
                  <h2 className="text-sm font-medium">{stage.label}</h2>
                  <p className="text-xs text-muted-foreground">{stage.blurb}</p>
                </div>

                <div className="grid gap-2.5 sm:grid-cols-2">
                  {items.map((provider) => (
                    <div
                      key={provider.id}
                      className="rounded-xl border border-border bg-card p-4"
                    >
                      <div className="flex items-start gap-3">
                        {provider.icon ? (
                          <span
                            className="flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-lg [&>svg]:size-8"
                            dangerouslySetInnerHTML={{ __html: provider.icon }}
                          />
                        ) : (
                          <span className="size-8 shrink-0 rounded-lg bg-muted" />
                        )}
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="truncate font-medium">{provider.name}</span>
                            <span className="font-mono text-[11px] text-muted-foreground">
                              {provider.id}
                            </span>
                          </div>
                          {provider.description ? (
                            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                              {provider.description}
                            </p>
                          ) : null}
                        </div>
                      </div>

                      <div className="mt-3 flex items-center gap-3 border-t border-border/60 pt-3 text-[11px]">
                        {provider.env?.length ? (
                          <span className="flex items-center gap-1 text-muted-foreground">
                            <KeyRound className="size-3" />
                            {provider.env.join(", ")}
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-success">
                            <Check className="size-3" />
                            runs locally
                          </span>
                        )}
                        {provider.docs_url ? (
                          <a
                            href={provider.docs_url}
                            target="_blank"
                            rel="noreferrer"
                            className="ml-auto flex items-center gap-1 text-muted-foreground hover:text-foreground"
                          >
                            Docs <ExternalLink className="size-3" />
                          </a>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      </div>
    </>
  );
}
