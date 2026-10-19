"use client";

import { Bell } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { cn } from "@/shared/lib/cn";
import { formatShortTime } from "@/shared/lib/format";
import { Button } from "@/shared/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/shared/ui/popover";
import { useMarkAllRead, useNotifications } from "../api";

/** Bell with an unread dot. `dark` sits on the sidebar, `light` in the mobile top bar. */
export function NotificationPopover({ tone }: { tone: "dark" | "light" }) {
  const [open, setOpen] = useState(false);
  const notifications = useNotifications();
  const markAllRead = useMarkAllRead();
  const unread = notifications.data?.unread ?? 0;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        aria-label={unread ? `Notifikasi, ${unread} belum dibaca` : "Notifikasi"}
        className={cn(
          "relative inline-flex items-center justify-center rounded-full outline-none focus-visible:outline-2 focus-visible:outline-offset-2",
          tone === "dark"
            ? "size-8 text-sidebar-foreground/80 hover:text-sidebar-foreground focus-visible:outline-sidebar-foreground"
            : "size-10.5 border border-border bg-card text-foreground focus-visible:outline-ring",
        )}
      >
        <Bell className="size-4.75" aria-hidden />
        {unread > 0 && (
          <span
            aria-hidden
            className={cn(
              "absolute size-2.25 rounded-full bg-brand",
              tone === "dark" ? "top-1 right-1" : "top-2 right-2 ring-2 ring-card",
            )}
          />
        )}
      </PopoverTrigger>
      <PopoverContent
        data-surface="v2"
        side="bottom"
        align={tone === "dark" ? "start" : "end"}
        className="w-[min(400px,calc(100vw-32px))] gap-0.5"
      >
        <div className="flex items-baseline justify-between px-3.5 pt-3.5 pb-2.5">
          <h2 className="font-display text-title-xs">Notifikasi</h2>
          {unread > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="-mr-2 text-caption text-muted-foreground"
              disabled={markAllRead.isPending}
              onClick={() => markAllRead.mutate()}
            >
              Tandai semua dibaca
            </Button>
          )}
        </div>
        <div className="flex max-h-[70dvh] flex-col gap-0.5 overflow-y-auto">
          {notifications.isPending && (
            <p className="px-3.5 py-4 text-caption text-muted-foreground">Memuat notifikasi…</p>
          )}
          {notifications.isError && (
            <div className="flex items-center justify-between gap-3 px-3.5 py-4">
              <p className="text-caption text-destructive">Notifikasi gagal dimuat.</p>
              <Button size="sm" variant="outline" onClick={() => notifications.refetch()}>
                Coba lagi
              </Button>
            </div>
          )}
          {notifications.isSuccess && notifications.data.items.length === 0 && (
            <p className="px-3.5 py-4 text-caption text-muted-foreground">Belum ada notifikasi.</p>
          )}
          {notifications.data?.items.map((item) => (
            <Link
              key={item.id}
              href={item.target}
              onClick={() => setOpen(false)}
              className={cn(
                "flex gap-3 rounded-field p-3.5 outline-none hover:bg-secondary focus-visible:bg-secondary",
                !item.read && "bg-background",
              )}
            >
              <Bell
                aria-hidden
                className={cn(
                  "mt-0.5 size-4.5 shrink-0",
                  item.read ? "text-faint-foreground" : "text-foreground",
                )}
              />
              <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="font-semibold text-sm">{item.title}</span>
                <span className="text-muted-foreground text-xs">{item.detail}</span>
              </span>
              <span className="shrink-0 text-faint-foreground text-xs">
                {formatShortTime(item.created_at)}
              </span>
              {!item.read && <span className="sr-only">Belum dibaca</span>}
            </Link>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}
