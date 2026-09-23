"use client";

import { Boxes, Radio, Settings, Waypoints } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Agents", icon: Waypoints, match: (p: string) => p === "/" || p.startsWith("/agents") || p === "/new" },
  { href: "/providers", label: "Providers", icon: Boxes, match: (p: string) => p.startsWith("/providers") },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="flex w-56 shrink-0 flex-col gap-1 border-r border-sidebar-border bg-sidebar px-3 py-4">
      <Link href="/" className="mb-5 flex items-center gap-2.5 px-2">
        <span className="flex size-8 items-center justify-center rounded-lg bg-primary/15 text-primary ring-1 ring-primary/25">
          <Radio className="size-4" />
        </span>
        <span className="text-[15px] font-semibold tracking-tight">Vocalis</span>
      </Link>

      {NAV.map(({ href, label, icon: Icon, match }) => (
        <Link
          key={href}
          href={href}
          className={cn(
            "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors",
            match(pathname)
              ? "bg-sidebar-accent text-sidebar-accent-foreground"
              : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
          )}
        >
          <Icon className="size-4" />
          {label}
        </Link>
      ))}

      <div className="mt-auto flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-muted-foreground/60">
        <Settings className="size-4" />
        Settings
        <span className="ml-auto text-[10px] uppercase tracking-wide">soon</span>
      </div>
    </nav>
  );
}
