"use client";

import { ChevronRight, LogOut, Monitor } from "lucide-react";
import Link from "next/link";
import { useMe } from "@/shared/api/generated";
import { AuthTransition } from "@/shared/ui/auth-transition";
import { Button } from "@/shared/ui/button";
import { usePolledAttendanceToday } from "../api";
import { initials, moreGroups, type NavItem, profile, workLocation } from "../nav";
import { roleLabels } from "../types";
import { useLogout } from "../use-logout";
import { StillWorkingNote } from "./account-menu";

/** S3 (Employee) and HM5 (Manager/HR): every page without a tab, the account, and Keluar. */
export function MorePage() {
  const me = useMe();
  const today = usePolledAttendanceToday();
  const { logout, signingOut } = useLogout();
  // The shell only renders its children once /me has loaded.
  if (!me.data) return null;
  const { user, tenant } = me.data;

  return (
    <div data-surface="v2" className="mx-auto flex w-full max-w-xl flex-col gap-3.5 pb-5">
      <section className="flex items-center gap-3.5 rounded-card bg-card p-4">
        <span className="flex size-13 shrink-0 items-center justify-center rounded-full bg-primary font-bold text-heading text-primary-foreground">
          {initials(user.name)}
        </span>
        <span className="flex min-w-0 flex-col gap-0.5">
          <span className="font-semibold text-body">{user.name}</span>
          <span className="text-caption text-faint-foreground">
            {roleLabels[user.role]} · {tenant.name}
          </span>
          <span className="text-caption text-faint-foreground">
            {user.department} · {workLocation(user)}
          </span>
        </span>
      </section>

      {moreGroups(user.role, user.department).map((group) => (
        <MoreGroup key={group.label} label={group.label ?? "Saya"}>
          {group.items.map((item) => (
            <MoreLink key={item.href} item={item} />
          ))}
        </MoreGroup>
      ))}

      <MoreGroup label="Akun">
        <MoreLink item={profile} />
      </MoreGroup>

      <Button
        variant="outline"
        size="lg"
        className="w-full text-destructive hover:text-destructive"
        disabled={signingOut}
        onClick={logout}
      >
        <LogOut />
        Keluar
      </Button>
      {today.data?.state === "checked_in" && <StillWorkingNote />}
      {signingOut && <AuthTransition message="Mengakhiri sesi…" />}
    </div>
  );
}

function MoreGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-faint-foreground text-overline uppercase">{label}</h2>
      <ul className="divide-y divide-border overflow-hidden rounded-card bg-card">{children}</ul>
    </section>
  );
}

function MoreLink({ item }: { item: NavItem }) {
  return (
    <li>
      <Link
        href={item.href}
        className="flex items-center gap-3 px-4 py-3.25 outline-none hover:bg-secondary focus-visible:bg-secondary"
      >
        <RowIcon icon={item.icon} />
        <span className="flex min-w-0 flex-1 flex-col gap-px">
          <span className="font-semibold text-sm">{item.label}</span>
          {item.description && (
            <span className="text-faint-foreground text-xs">{item.description}</span>
          )}
        </span>
        {item.desktopOnly ? (
          <span className="inline-flex items-center gap-1 rounded-md bg-background px-2 py-0.75 font-semibold text-faint-foreground text-xs">
            <Monitor aria-hidden className="size-3" />
            Desktop
          </span>
        ) : (
          <ChevronRight aria-hidden className="size-4.25 text-faint-foreground" />
        )}
      </Link>
    </li>
  );
}

function RowIcon({ icon: Icon }: { icon: NavItem["icon"] }) {
  return (
    <span className="flex size-8.5 shrink-0 items-center justify-center rounded-control bg-background text-muted-foreground">
      <Icon aria-hidden className="size-4.25" />
    </span>
  );
}
