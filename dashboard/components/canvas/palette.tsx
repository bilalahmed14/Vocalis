"use client";

import { NODE_TYPES, type NodeType } from "@/lib/schema/ports";
import { useProviders } from "@/components/canvas/providers-context";

const TYPE_LABEL: Record<NodeType, string> = {
  vad: "Voice activity",
  stt: "Speech to text",
  llm: "Language model",
  tts: "Text to speech",
};

export function Palette({ onAdd }: { onAdd: (type: NodeType, providerId: string) => void }) {
  const providers = useProviders();

  return (
    <aside className="flex w-60 shrink-0 flex-col gap-4 overflow-y-auto border-r bg-background p-3">
      <div>
        <h2 className="text-sm font-semibold">Providers</h2>
        <p className="text-xs text-muted-foreground">Drag onto the canvas, or click to add.</p>
      </div>

      {NODE_TYPES.map((type) => (
        <section key={type} className="space-y-1.5">
          <h3 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            {TYPE_LABEL[type]}
          </h3>
          {providers
            .filter((provider) => provider.type === type)
            .map((provider) => (
              <button
                key={provider.id}
                type="button"
                draggable
                onDragStart={(event) => {
                  event.dataTransfer.setData("application/vocalis", `${type}:${provider.id}`);
                  event.dataTransfer.effectAllowed = "move";
                }}
                onClick={() => onAdd(type, provider.id)}
                className="flex w-full cursor-grab items-center gap-2 rounded-md border bg-card px-2 py-1.5 text-left text-sm hover:border-primary hover:bg-accent"
                title={provider.description}
              >
                {provider.icon ? (
                  <span className="size-4 shrink-0" dangerouslySetInnerHTML={{ __html: provider.icon }} />
                ) : (
                  <span className="size-4 shrink-0 rounded bg-muted" />
                )}
                <span className="truncate">{provider.name}</span>
                {provider.env && provider.env.length > 0 ? (
                  <span className="ml-auto text-[10px] text-muted-foreground" title={provider.env.join(", ")}>
                    key
                  </span>
                ) : (
                  <span className="ml-auto text-[10px] text-muted-foreground">local</span>
                )}
              </button>
            ))}
        </section>
      ))}
    </aside>
  );
}
