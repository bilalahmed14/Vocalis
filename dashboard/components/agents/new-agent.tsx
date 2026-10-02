"use client";

import { Check, KeyRound, Loader2, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type Template } from "@/lib/api";
import { emptyConfig } from "@/lib/agent/config";
import { cn } from "@/lib/utils";

const BLANK = "blank";

export function NewAgent({ templates }: { templates: Template[] }) {
  const router = useRouter();
  const [choice, setChoice] = useState<string>(templates[0]?.id ?? BLANK);
  const [name, setName] = useState("");
  const [error, setError] = useState<string>();
  const [creating, setCreating] = useState(false);

  const template = templates.find((candidate) => candidate.id === choice);
  const defaultName = template ? `${template.name} copy` : "New agent";

  const create = async () => {
    setCreating(true);
    setError(undefined);
    const config = template
      ? { ...template.config, name: name || defaultName }
      : { ...emptyConfig(name || defaultName) };

    try {
      if (!template) {
        // A blank agent has no nodes yet, so it can't be saved until it's built.
        sessionStorage.setItem("vocalis:draft", JSON.stringify(config));
        router.push("/new/canvas");
        return;
      }
      const saved = await api.create(config, "created from template");
      router.push(`/agents/${saved.slug}`);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "could not create the agent");
      setCreating(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <h1 className="text-xl font-semibold tracking-tight">New agent</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Start from a working pipeline, or from an empty canvas.
      </p>

      <div className="mt-6 space-y-2">
        {templates.map((candidate) => (
          <button
            key={candidate.id}
            type="button"
            onClick={() => setChoice(candidate.id)}
            className={cn(
              "flex w-full items-start gap-3 rounded-xl border p-4 text-left transition-colors",
              choice === candidate.id
                ? "border-primary bg-accent/40"
                : "border-border bg-card hover:border-border/80 hover:bg-accent/20",
            )}
          >
            <span
              className={cn(
                "mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full border",
                choice === candidate.id ? "border-primary bg-primary" : "border-muted-foreground",
              )}
            >
              {choice === candidate.id ? (
                <Check className="size-3 text-primary-foreground" />
              ) : null}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block font-medium">{candidate.name}</span>
              <span className="mt-0.5 block text-sm text-muted-foreground">
                {candidate.description}
              </span>
              <span className="mt-2 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                {candidate.needs_keys.length ? (
                  <>
                    <KeyRound className="size-3" />
                    needs {candidate.needs_keys.join(", ")}
                  </>
                ) : (
                  <>
                    <Sparkles className="size-3 text-success" />
                    <span className="text-success">runs locally, no API keys</span>
                  </>
                )}
              </span>
            </span>
          </button>
        ))}

        <button
          type="button"
          onClick={() => setChoice(BLANK)}
          className={cn(
            "flex w-full items-center gap-3 rounded-xl border p-4 text-left transition-colors",
            choice === BLANK
              ? "border-primary bg-accent/40"
              : "border-border bg-card hover:border-border/80 hover:bg-accent/20",
          )}
        >
          <span
            className={cn(
              "flex size-4 shrink-0 items-center justify-center rounded-full border",
              choice === BLANK ? "border-primary bg-primary" : "border-muted-foreground",
            )}
          >
            {choice === BLANK ? <Check className="size-3 text-primary-foreground" /> : null}
          </span>
          <span>
            <span className="block font-medium">Empty canvas</span>
            <span className="text-sm text-muted-foreground">Patch it together yourself.</span>
          </span>
        </button>
      </div>

      <div className="mt-6 space-y-1.5">
        <Label htmlFor="agent-name" className="text-xs text-muted-foreground">
          Name
        </Label>
        <Input
          id="agent-name"
          placeholder={defaultName}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </div>

      {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}

      <div className="mt-6 flex items-center gap-3">
        <Button onClick={create} disabled={creating} className="gap-1.5">
          {creating ? <Loader2 className="size-4 animate-spin" /> : null}
          Create agent
        </Button>
        <Button variant="ghost" onClick={() => router.push("/")}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
