"use client";

import Link from "next/link";
import { cn } from "@/shared/lib/cn";
import { BrandLogo } from "@/shared/ui/brand-logo";
import { activeHref, type NavGroup } from "../nav";
import type { Me } from "../types";
import { AccountMenu } from "./account-menu";
import { NotificationPopover } from "./notification-popover";

/** S1: dark desktop sidebar, no top bar. Hidden below `lg`, where the tab bar takes over. */
export function Sidebar({
  me,
  groups,
  pathname,
  pendingApprovals,
  stillWorking,
  onLogout,
}: {
  me: Me;
  groups: NavGroup[];
  pathname: string;
  pendingApprovals: number;
  stillWorking: boolean;
  onLogout: () => void;
}) {
  const current = activeHref(
    pathname,
    groups.filter((group) => !group.shortcuts).flatMap((group) => group.items.map((i) => i.href)),
  );

  return (
    <aside
      data-surface="v2"
      className="sticky top-0 hidden h-dvh w-68 shrink-0 flex-col gap-6 overflow-y-auto bg-sidebar px-4 pt-7 pb-5 text-sidebar-foreground lg:flex"
    >
      <div className="flex items-center justify-between px-2.5">
        <Link
          href="/app/overview"
          className="rounded-control outline-none focus-visible:outline-2 focus-visible:outline-sidebar-foreground"
        >
          <BrandLogo variant="white" className="h-7 w-auto" />
        </Link>
        <NotificationPopover tone="dark" />
      </div>

      {groups.map((group) => (
        <nav key={group.label ?? "main"} aria-label={group.label ?? "Saya"}>
          {group.label && (
            <p className="px-3 pb-1.5 text-caption text-sidebar-foreground/40">{group.label}</p>
          )}
          <ul className="flex flex-col gap-0.5">
            {group.items.map((item) => {
              const active = !group.shortcuts && item.href === current;
              const Icon = item.icon;
              return (
                <li key={`${group.label}-${item.label}`}>
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-3.5 rounded-control px-3 outline-none transition-colors hover:bg-sidebar-foreground/5 focus-visible:outline-2 focus-visible:outline-sidebar-foreground",
                      group.shortcuts
                        ? "h-10 text-sidebar-foreground/60 text-sm"
                        : "h-10 text-body text-sidebar-foreground/70",
                      active && "bg-sidebar-foreground/10 text-sidebar-foreground",
                    )}
                  >
                    <Icon
                      aria-hidden
                      className={cn(
                        group.shortcuts ? "size-4.25 opacity-75" : "size-4.5 opacity-85",
                        active && "opacity-100",
                      )}
                    />
                    <span className="flex-1">{item.label}</span>
                    {item.approvalsBadge && pendingApprovals > 0 && (
                      <span className="rounded-control bg-brand px-2 py-0.5 font-bold text-sidebar-foreground text-xs">
                        {pendingApprovals}
                        <span className="sr-only"> menunggu</span>
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      ))}

      <div className="mt-auto">
        <AccountMenu me={me} stillWorking={stillWorking} onLogout={onLogout} />
      </div>
    </aside>
  );
}
