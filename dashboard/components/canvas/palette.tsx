"use client";

import { KeyRound, Search } from "lucide-react";
import { useState } from "react";

import { useProviders } from "@/components/canvas/providers-context";
import { NODE_TYPES, type NodeType } from "@/lib/schema/ports";
import { STAGE } from "@/lib/schema/stages";

export function Palette({ onAdd }: { onAdd: (type: NodeType, providerId: string) => void }) {
  const providers = useProviders();
  const [query, setQuery] = useState("");

  const matches = providers.filter((provider) =>
    `${provider.name} ${provider.id} ${provider.type}`.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-sidebar">
      <div className="border-b border-border p-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search providers"
            className="h-8 w-full rounded-lg border border-input bg-background pl-8 pr-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring"
          />
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-3">
        {NODE_TYPES.map((type) => {
          const stage = STAGE[type];
          const items = matches.filter((provider) => provider.type === type);
          if (!items.length) return null;

          return (
            <section key={type}>
              <div className="mb-1.5 flex items-center gap-1.5 px-0.5">
                <span className="size-1.5 rounded-full" style={{ background: stage.color }} />
                <h3 className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  {stage.label}
                </h3>
              </div>

              <div className="space-y-1">
                {items.map((provider) => (
                  <button
                    key={provider.id}
                    type="button"
                    draggable
                    onDragStart={(event) => {
                      event.dataTransfer.setData("application/vocalis", `${type}:${provider.id}`);
                      event.dataTransfer.effectAllowed = "move";
                    }}
                    onClick={() => onAdd(type, provider.id)}
                    title={provider.description}
                    className="flex w-full cursor-grab items-center gap-2.5 rounded-lg border border-transparent bg-card/60 px-2 py-1.5 text-left transition-colors hover:border-border hover:bg-accent/50 active:cursor-grabbing"
                  >
                    {provider.icon ? (
                      <span
                        className="flex size-6 shrink-0 items-center justify-center overflow-hidden rounded [&>svg]:size-6"
                        dangerouslySetInnerHTML={{ __html: provider.icon }}
                      />
                    ) : (
                      <span className="size-6 shrink-0 rounded bg-muted" />
                    )}
                    <span className="min-w-0 flex-1 truncate text-sm">{provider.name}</span>
                    {provider.env?.length ? (
                      <KeyRound
                        className="size-3 shrink-0 text-muted-foreground/60"
                        aria-label={`needs ${provider.env.join(", ")}`}
                      />
                    ) : (
                      <span className="shrink-0 rounded bg-success/10 px-1 py-0.5 text-[9px] font-medium uppercase tracking-wide text-success">
                        local
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </section>
          );
        })}

        {matches.length === 0 ? (
          <p className="px-1 py-6 text-center text-xs text-muted-foreground">
            Nothing matches “{query}”.
          </p>
        ) : null}
      </div>

      <p className="border-t border-border px-3 py-2.5 text-[11px] leading-snug text-muted-foreground">
        Drag onto the canvas, or click to add. Cables only connect matching ports.
      </p>
    </aside>
  );
}
