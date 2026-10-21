"use client";

import { Button } from "@/shared/ui/button";
import { useMarkAllRead, useNotifications } from "../api";
import { groupByDay } from "../notifications";
import { NotificationCard, NotificationStates } from "./notification-item";

/** S4: every notification, newest first, grouped into Hari ini and Sebelumnya. */
export function NotificationsPage() {
  const notifications = useNotifications();
  const markAllRead = useMarkAllRead();
  const unread = notifications.data?.unread ?? 0;

  return (
    <div data-surface="v2" className="mx-auto flex w-full max-w-xl flex-col gap-5 pb-5">
      <div className="flex items-center justify-between gap-3">
        <p className="font-semibold text-caption text-faint-foreground">
          {unread ? `${unread} belum dibaca` : "Semua sudah dibaca"}
        </p>
        {unread > 0 && (
          <Button
            variant="ghost"
            size="sm"
            className="-mr-2 font-bold text-caption"
            disabled={markAllRead.isPending}
            onClick={() => markAllRead.mutate()}
          >
            Tandai semua dibaca
          </Button>
        )}
      </div>

      <NotificationStates notifications={notifications} />
      {notifications.data &&
        groupByDay(notifications.data.items).map((group) => (
          <section key={group.label} className="flex flex-col gap-2">
            <h2 className="font-bold text-caption text-faint-foreground">{group.label}</h2>
            {group.items.map((item) => (
              <NotificationCard key={item.id} item={item} />
            ))}
          </section>
        ))}
    </div>
  );
}
