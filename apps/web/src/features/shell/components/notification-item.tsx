"use client";

import Link from "next/link";
import { useReadNotification } from "@/shared/api/generated";
import type { NotificationOut } from "@/shared/api/generated/model";
import { cn } from "@/shared/lib/cn";
import { formatShortTime } from "@/shared/lib/format";
import { Button } from "@/shared/ui/button";
import type { usePolledNotifications } from "../api";
import { notificationIcon } from "../notifications";

/** Opening a notification marks it read, then follows its target. */
function useOpen(item: NotificationOut, onOpen?: () => void) {
  const markRead = useReadNotification();
  return () => {
    if (!item.read) markRead.mutate({ notificationId: item.id });
    onOpen?.();
  };
}

/** D6 panel row: unread rows sit on the canvas tone; the time stays on the right. */
export function NotificationRow({ item, onOpen }: { item: NotificationOut; onOpen: () => void }) {
  const open = useOpen(item, onOpen);
  const Icon = notificationIcon(item.target);
  return (
    <Link
      href={item.target}
      onClick={open}
      className={cn(
        "flex gap-3 rounded-field p-3.5 outline-none hover:bg-secondary focus-visible:bg-secondary",
        !item.read && "bg-background",
      )}
    >
      <Icon
        aria-hidden
        className={cn(
          "mt-0.5 size-4.5 shrink-0",
          item.read ? "text-faint-foreground" : "text-foreground",
        )}
      />
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className={cn("text-sm", item.read ? "font-medium" : "font-semibold")}>
          {item.title}
        </span>
        <span className="text-caption text-faint-foreground">{item.detail}</span>
      </span>
      <span className="shrink-0 font-medium text-faint-foreground text-xs">
        {formatShortTime(item.created_at)}
      </span>
      {!item.read && <span className="sr-only">Belum dibaca</span>}
    </Link>
  );
}

/** S4 card: unread cards are white with a line and a red dot; read ones sink to the subtle tone. */
export function NotificationCard({ item }: { item: NotificationOut }) {
  const open = useOpen(item);
  const Icon = notificationIcon(item.target);
  return (
    <Link
      href={item.target}
      onClick={open}
      className={cn(
        "flex gap-3 rounded-tile p-3.5 outline-none focus-visible:outline-2 focus-visible:outline-ring",
        item.read ? "bg-subtle" : "border border-border bg-card",
      )}
    >
      {/* The mockup tints this circle per type; the API sends no type yet, so it stays neutral. */}
      <span className="flex size-9.5 shrink-0 items-center justify-center rounded-full bg-secondary">
        <Icon aria-hidden className="size-4.5 text-muted-foreground" />
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-0.75">
        <span className="flex items-center gap-2">
          <span className="flex-1 font-bold text-sm">{item.title}</span>
          {!item.read && (
            <span className="size-2 shrink-0 rounded-full bg-brand">
              <span className="sr-only">Belum dibaca</span>
            </span>
          )}
        </span>
        <span className="text-caption text-muted-foreground">{item.detail}</span>
        <span className="font-medium text-faint-foreground text-xs">
          {formatShortTime(item.created_at)}
        </span>
      </span>
    </Link>
  );
}

/** Loading, error and empty states, the same in D6 and S4. Renders nothing once items exist. */
export function NotificationStates({
  notifications,
}: {
  notifications: ReturnType<typeof usePolledNotifications>;
}) {
  if (notifications.isPending)
    return (
      <p role="status" className="px-3.5 py-4 text-caption text-muted-foreground">
        Memuat notifikasi…
      </p>
    );
  if (notifications.isError && !notifications.data)
    return (
      <div role="alert" className="flex items-center justify-between gap-3 px-3.5 py-4">
        <p className="text-caption text-destructive">Notifikasi gagal dimuat.</p>
        <Button size="sm" variant="outline" onClick={() => notifications.refetch()}>
          Coba lagi
        </Button>
      </div>
    );
  if (notifications.data?.items.length === 0)
    return <p className="px-3.5 py-4 text-caption text-muted-foreground">Belum ada notifikasi.</p>;
  return null;
}
