"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const TABS = [
  { label: "Pipeline", path: "" },
  { label: "Calls", path: "/calls" },
  { label: "Settings", path: "/settings" },
];

export function AgentTabs({ slug }: { slug: string }) {
  const pathname = usePathname();
  const base = `/agents/${slug}`;

  return (
    <nav className="flex gap-1">
      {TABS.map((tab) => {
        const href = `${base}${tab.path}`;
        const active = tab.path ? pathname.startsWith(href) : pathname === base;
        return (
          <Link
            key={tab.label}
            href={href}
            className={cn(
              "rounded-lg px-2.5 py-1.5 text-sm transition-colors",
              active
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
