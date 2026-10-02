"use client";

import { Boxes, FlaskConical, Gauge, PhoneCall, Settings, Waypoints } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { CommandMenu } from "@/components/shell/command-menu";
import { cn } from "@/lib/utils";

type Item = {
  href: string;
  label: string;
  icon: typeof Gauge;
  match: (path: string) => boolean;
  soon?: boolean;
};

const GROUPS: { title: string; items: Item[] }[] = [
  {
    title: "Measure",
    items: [
      { href: "/", label: "Overview", icon: Gauge, match: (p) => p === "/" },
      { href: "/calls", label: "Calls", icon: PhoneCall, match: (p) => p.startsWith("/calls") },
    ],
  },
  {
    title: "Patch",
    items: [
      {
        href: "/agents",
        label: "Agents",
        icon: Waypoints,
        match: (p) => p.startsWith("/agents") || p.startsWith("/new"),
      },
      {
        href: "/providers",
        label: "Providers",
        icon: Boxes,
        match: (p) => p.startsWith("/providers"),
      },
    ],
  },
  {
    title: "Compare",
    items: [{ href: "#", label: "Evals", icon: FlaskConical, match: () => false, soon: true }],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="flex w-52 shrink-0 flex-col gap-6 border-r border-sidebar-border bg-sidebar px-3 py-5">
      <Link href="/" className="flex items-baseline gap-2 px-2">
        <span className="display text-xl leading-none">Vocalis</span>
        <span className="silkscreen">v1</span>
      </Link>

      <CommandMenu />

      {GROUPS.map((group) => (
        <div key={group.title} className="space-y-0.5">
          <h2 className="silkscreen px-2 pb-1.5">{group.title}</h2>
          {group.items.map(({ href, label, icon: Icon, match, soon }) =>
            soon ? (
              <div
                key={label}
                className="flex items-center gap-2.5 px-2 py-1.5 text-sm text-muted-foreground/45"
              >
                <Icon className="size-3.5" />
                {label}
                <span className="ml-auto text-[9px] uppercase tracking-[0.12em]">soon</span>
              </div>
            ) : (
              <Link
                key={label}
                href={href}
                className={cn(
                  "group relative flex items-center gap-2.5 px-2 py-1.5 text-sm transition-colors",
                  match(pathname)
                    ? "text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {/* The lit channel on a console strip. */}
                <span
                  className={cn(
                    "absolute left-0 top-1/2 h-4 w-px -translate-y-1/2 transition-colors",
                    match(pathname) ? "bg-primary" : "bg-transparent group-hover:bg-border",
                  )}
                />
                <Icon className="size-3.5" />
                {label}
              </Link>
            ),
          )}
        </div>
      ))}

      <div className="mt-auto flex items-center gap-2.5 px-2 py-1.5 text-sm text-muted-foreground/45">
        <Settings className="size-3.5" />
        Settings
        <span className="ml-auto text-[9px] uppercase tracking-[0.12em]">soon</span>
      </div>
    </nav>
  );
}
