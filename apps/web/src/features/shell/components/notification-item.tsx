"use client";

import Link from "next/link";
import { cn } from "@/shared/lib/cn";
import { formatShortTime } from "@/shared/lib/format";
import { useMarkRead } from "../api";
import { notificationIcon } from "../notifications";
import type { Notification } from "../types";

/** One notification, shared by D6 and S4. Opening it marks it read. */
export function NotificationItem({
  item,
  onOpen,
  className,
}: {
  item: Notification;
  onOpen?: () => void;
  className?: string;
}) {
  const markRead = useMarkRead();
  const Icon = notificationIcon(item.target);

  return (
    <Link
      href={item.target}
      onClick={() => {
        if (!item.read) markRead.mutate(item.id);
        onOpen?.();
      }}
      className={cn(
        "flex gap-3 rounded-field p-3.5 outline-none hover:bg-secondary focus-visible:bg-secondary",
        className,
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
        <span className="font-semibold text-sm">{item.title}</span>
        <span className="text-muted-foreground text-xs">{item.detail}</span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-1.5">
        <span className="text-faint-foreground text-xs">{formatShortTime(item.created_at)}</span>
        {!item.read && (
          <span className="size-2 rounded-full bg-brand">
            <span className="sr-only">Belum dibaca</span>
          </span>
        )}
      </span>
    </Link>
  );
}
