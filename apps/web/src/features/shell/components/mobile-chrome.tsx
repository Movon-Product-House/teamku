"use client";

import Link from "next/link";
import { cn } from "@/shared/lib/cn";
import { activeTab, initials, MORE_HREF, type NavItem } from "../nav";
import type { Role } from "../types";
import { NotificationPopover } from "./notification-popover";

/** S2 top bar: page title, bell, and the avatar that opens Lainnya. */
export function MobileHeader({ title, name }: { title: string; name: string }) {
  return (
    <header
      data-surface="v2"
      className="flex items-center justify-between gap-3 px-5 pt-3 pb-2 lg:hidden"
    >
      <p className="truncate font-display text-title-sm">{title}</p>
      <div className="flex items-center gap-2">
        <NotificationPopover tone="light" />
        <Link
          href={MORE_HREF}
          aria-label="Akun dan menu lainnya"
          className="flex size-10.5 items-center justify-center rounded-full bg-primary font-bold text-primary-foreground text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          {initials(name)}
        </Link>
      </div>
    </header>
  );
}

/** S2 tab bar: four tabs, floating at the bottom on phones and tablets. */
export function TabBar({
  items,
  role,
  pathname,
  pendingApprovals,
}: {
  items: NavItem[];
  role: Role;
  pathname: string;
  pendingApprovals: number;
}) {
  const current = activeTab(pathname, role);
  return (
    <nav
      data-surface="v2"
      aria-label="Navigasi utama"
      className="fixed inset-x-0 bottom-0 z-40 px-4 pt-2 pb-[max(12px,env(safe-area-inset-bottom))] lg:hidden"
    >
      <ul className="flex h-16 gap-1 rounded-full border border-border bg-card/95 p-1.5 shadow-float backdrop-blur">
        {items.map((item) => {
          const active = item.href === current;
          const Icon = item.icon;
          return (
            <li key={item.href} className="flex flex-1">
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "relative flex flex-1 flex-col items-center justify-center gap-0.75 rounded-full font-semibold text-xs outline-none focus-visible:outline-2 focus-visible:outline-ring",
                  active ? "bg-secondary text-foreground" : "text-faint-foreground",
                )}
              >
                <span className="relative">
                  <Icon aria-hidden className="size-5.5" />
                  {item.approvalsBadge && pendingApprovals > 0 && (
                    <span className="absolute -top-1.5 -right-2.5 min-w-4.5 rounded-full bg-brand px-1 text-center font-bold text-primary-foreground text-xs leading-4.5">
                      {pendingApprovals}
                      <span className="sr-only"> menunggu</span>
                    </span>
                  )}
                </span>
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
