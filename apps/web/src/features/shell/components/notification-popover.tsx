"use client";

import { Bell } from "lucide-react";
import { useState } from "react";
import { useReadNotifications } from "@/shared/api/generated";
import { Button } from "@/shared/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/shared/ui/popover";
import { usePolledNotifications } from "../api";
import { NotificationRow, NotificationStates } from "./notification-item";

export function unreadLabel(unread: number): string {
  return unread ? `Notifikasi, ${unread} belum dibaca` : "Notifikasi";
}

/** D6: sidebar bell with an unread dot, opening the notification panel. */
export function NotificationPopover() {
  const [open, setOpen] = useState(false);
  const notifications = usePolledNotifications();
  const markAllRead = useReadNotifications();
  const unread = notifications.data?.unread ?? 0;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        aria-label={unreadLabel(unread)}
        className="relative inline-flex size-8 items-center justify-center rounded-full text-sidebar-foreground/80 outline-none hover:text-sidebar-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sidebar-foreground"
      >
        <Bell className="size-4.75" aria-hidden />
        {unread > 0 && (
          <span aria-hidden className="absolute top-1 right-1 size-2.25 rounded-full bg-brand" />
        )}
      </PopoverTrigger>
      <PopoverContent
        data-surface="v2"
        side="bottom"
        align="start"
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
          <NotificationStates notifications={notifications} />
          {notifications.data?.items.map((item) => (
            <NotificationRow key={item.id} item={item} onOpen={() => setOpen(false)} />
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}
