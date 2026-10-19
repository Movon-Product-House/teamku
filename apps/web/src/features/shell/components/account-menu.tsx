"use client";

import { ChevronsUpDown, LogOut, ShieldCheck } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { initials, workLocation } from "../nav";
import { type Me, roleLabels } from "../types";

/** S3 on desktop: opened from the name at the bottom of the sidebar. */
export function AccountMenu({
  me,
  stillWorking,
  onLogout,
}: {
  me: Me;
  stillWorking: boolean;
  onLogout: () => void;
}) {
  const { user, tenant } = me;
  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex w-full items-center gap-3 rounded-field px-3 py-2.5 text-left outline-none hover:bg-sidebar-foreground/5 focus-visible:outline-2 focus-visible:outline-sidebar-foreground aria-expanded:bg-sidebar-foreground/10">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-control bg-sidebar-foreground/12 font-bold text-xs">
          {initials(user.name)}
        </span>
        <span className="flex min-w-0 flex-1 flex-col gap-px">
          <span className="truncate font-semibold text-sm">{user.name}</span>
          <span className="truncate text-sidebar-foreground/45 text-xs">
            {roleLabels[user.role]} · {tenant.name}
          </span>
        </span>
        <ChevronsUpDown aria-hidden className="size-4 shrink-0 text-sidebar-foreground/45" />
      </DropdownMenuTrigger>
      <DropdownMenuContent data-surface="v2" side="top" align="start" className="w-65 gap-0.5">
        <div className="flex flex-col gap-0.5 px-3 pt-3 pb-3.5">
          <p className="font-semibold text-body">{user.name}</p>
          <p className="truncate text-caption text-faint-foreground">{user.email}</p>
          <p className="text-caption text-faint-foreground">
            {roleLabels[user.role]} · {user.department} · {workLocation(user)}
          </p>
        </div>
        <DropdownMenuSeparator />
        {/* P7 is built in #17; the item stays visible so the menu matches the mockup. */}
        <DropdownMenuItem disabled>
          <ShieldCheck className="text-muted-foreground" />
          Profil & keamanan
          <span className="ml-auto text-faint-foreground text-xs">Segera</span>
        </DropdownMenuItem>
        <DropdownMenuItem variant="destructive" onSelect={onLogout}>
          <LogOut />
          Keluar
        </DropdownMenuItem>
        {stillWorking && <StillWorkingNote />}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function StillWorkingNote() {
  return (
    <p className="rounded-control bg-warning-muted p-2.5 font-semibold text-foreground text-xs">
      Kamu masih Sedang bekerja. Keluar tidak menutup presensi.
    </p>
  );
}
