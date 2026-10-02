"use client";

import { PhoneCall, Plus, Search, Waypoints } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { api, type AgentSummary } from "@/lib/api";
import { cn } from "@/lib/utils";

type Entry = { label: string; hint?: string; href: string; icon: typeof Search };

const PAGES: Entry[] = [
  { label: "New agent", href: "/new", icon: Plus },
  { label: "Agents", href: "/agents", icon: Waypoints },
  { label: "Calls", href: "/calls", icon: PhoneCall },
];

/** Jump anywhere with ⌘K: pages, and any saved agent by name. */
export function CommandMenu() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [selected, setSelected] = useState(0);

  const show = useCallback((next: boolean) => {
    setOpen(next);
    setQuery("");
    setSelected(0);
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen((current) => {
          if (current) setQuery("");
          return !current;
        });
      }
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) void api.agents().then(setAgents).catch(() => setAgents([]));
  }, [open]);

  const entries = useMemo(() => {
    const all: Entry[] = [
      ...PAGES,
      ...agents.map((agent) => ({
        label: agent.name,
        hint: `v${agent.version}`,
        href: `/agents/${agent.slug}`,
        icon: Waypoints,
      })),
    ];
    const needle = query.toLowerCase();
    return all.filter((entry) => entry.label.toLowerCase().includes(needle));
  }, [agents, query]);

  const go = useCallback(
    (href: string) => {
      show(false);
      router.push(href);
    },
    [router, show],
  );

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => show(true)}
        className="flex w-full items-center gap-2 rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm text-muted-foreground hover:border-ring"
      >
        <Search className="size-3.5" />
        Search
        <kbd className="ml-auto rounded border border-border px-1 font-mono text-[10px]">⌘K</kbd>
      </button>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-background/70 pt-32 backdrop-blur-sm"
      onClick={() => show(false)}
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-xl border border-border bg-popover shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center gap-2 border-b border-border px-3">
          <Search className="size-4 text-muted-foreground" />
          <input
            autoFocus
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setSelected(0);
            }}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown")
                setSelected((index) => Math.min(index + 1, entries.length - 1));
              if (event.key === "ArrowUp") setSelected((index) => Math.max(index - 1, 0));
              if (event.key === "Enter" && entries[selected]) go(entries[selected].href);
            }}
            placeholder="Go to an agent or a page…"
            className="h-11 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
        </div>

        <ul className="max-h-72 overflow-y-auto p-1.5">
          {entries.map((entry, index) => (
            <li key={`${entry.href}-${entry.label}`}>
              <button
                type="button"
                onMouseEnter={() => setSelected(index)}
                onClick={() => go(entry.href)}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm",
                  index === selected ? "bg-accent text-accent-foreground" : "text-foreground",
                )}
              >
                <entry.icon className="size-4 text-muted-foreground" />
                {entry.label}
                {entry.hint ? (
                  <span className="ml-auto font-mono text-[11px] text-muted-foreground">
                    {entry.hint}
                  </span>
                ) : null}
              </button>
            </li>
          ))}
          {entries.length === 0 ? (
            <li className="px-2.5 py-6 text-center text-sm text-muted-foreground">
              Nothing matches “{query}”.
            </li>
          ) : null}
        </ul>
      </div>
    </div>
  );
}
