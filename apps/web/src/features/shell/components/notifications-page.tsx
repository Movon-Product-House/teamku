"use client";

import { Button } from "@/shared/ui/button";
import { useMarkAllRead, useNotifications } from "../api";
import { groupByDay } from "../notifications";
import { NotificationItem } from "./notification-item";

/** S4: every notification, newest first, grouped into Hari ini and Sebelumnya. */
export function NotificationsPage() {
  const notifications = useNotifications();
  const markAllRead = useMarkAllRead();
  const unread = notifications.data?.unread ?? 0;

  return (
    <div data-surface="v2" className="mx-auto flex w-full max-w-xl flex-col gap-3.5 pb-5">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-caption text-muted-foreground">
          {unread ? `${unread} belum dibaca` : "Semua sudah dibaca"}
        </p>
        {unread > 0 && (
          <Button
            variant="ghost"
            size="sm"
            className="-mr-2 font-semibold text-caption"
            disabled={markAllRead.isPending}
            onClick={() => markAllRead.mutate()}
          >
            Tandai semua dibaca
          </Button>
        )}
      </div>

      {notifications.isPending && (
        <p role="status" className="py-4 text-caption text-muted-foreground">
          Memuat notifikasi…
        </p>
      )}
      {notifications.isError && !notifications.data && (
        <div
          role="alert"
          className="flex items-center justify-between gap-3 rounded-card bg-card p-4"
        >
          <p className="text-caption text-destructive">Notifikasi gagal dimuat.</p>
          <Button size="sm" variant="outline" onClick={() => notifications.refetch()}>
            Coba lagi
          </Button>
        </div>
      )}
      {notifications.isSuccess && notifications.data.items.length === 0 && (
        <p className="rounded-card bg-card p-4 text-caption text-muted-foreground">
          Belum ada notifikasi.
        </p>
      )}

      {notifications.data &&
        groupByDay(notifications.data.items).map((group) => (
          <section key={group.label} className="flex flex-col gap-2">
            <h2 className="text-caption text-faint-foreground">{group.label}</h2>
            <div className="flex flex-col gap-1 rounded-card bg-card p-1.5">
              {group.items.map((item) => (
                <NotificationItem key={item.id} item={item} />
              ))}
            </div>
          </section>
        ))}
    </div>
  );
}
