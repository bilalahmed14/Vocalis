"use client";

import { Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { AgentConfig } from "@/lib/schema/agent.gen";

export function AgentSettings({ slug, config }: { slug: string; config: AgentConfig }) {
  const router = useRouter();
  const [name, setName] = useState(config.name);
  const [description, setDescription] = useState(config.description ?? "");
  const [state, setState] = useState<{ kind: "idle" | "saving" | "saved" | "error"; message?: string }>({
    kind: "idle",
  });

  const changed = name !== config.name || description !== (config.description ?? "");

  const save = async () => {
    setState({ kind: "saving" });
    try {
      const saved = await api.save(slug, {
        ...config,
        name,
        ...(description ? { description } : {}),
      });
      setState({ kind: "saved", message: `saved v${saved.version}` });
      router.refresh();
    } catch (error) {
      setState({ kind: "error", message: error instanceof Error ? error.message : "save failed" });
    }
  };

  const remove = async () => {
    if (!confirm(`Delete "${config.name}" and all of its versions? This can't be undone.`)) return;
    await api.remove(slug);
    router.push("/");
    router.refresh();
  };

  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
      <div className="mx-auto max-w-2xl space-y-6">
        <section className="space-y-4 rounded-xl border border-border bg-card p-5">
          <div className="space-y-1.5">
            <Label htmlFor="name" className="text-xs text-muted-foreground">
              Name
            </Label>
            <Input id="name" value={name} onChange={(event) => setName(event.target.value)} />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="description" className="text-xs text-muted-foreground">
              Description
            </Label>
            <Textarea
              id="description"
              rows={3}
              placeholder="What this agent is for."
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>

          <div className="flex items-center gap-3">
            <Button size="sm" onClick={save} disabled={!changed || state.kind === "saving"}>
              {state.kind === "saving" ? "Saving…" : "Save as new version"}
            </Button>
            <span
              className={`text-xs ${state.kind === "error" ? "text-destructive" : "text-muted-foreground"}`}
            >
              {state.message}
            </span>
          </div>
        </section>

        <section className="space-y-3 rounded-xl border border-destructive/30 bg-destructive/5 p-5">
          <div>
            <h2 className="text-sm font-medium">Delete this agent</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Removes every version. Call logs keep their own copy of the config, so they stay
              readable.
            </p>
          </div>
          <Button size="sm" variant="destructive" onClick={remove} className="gap-1.5">
            <Trash2 className="size-4" />
            Delete agent
          </Button>
        </section>
      </div>
    </div>
  );
}
