import { Bell, CalendarDays, type LucideIcon, ReceiptText, ScanFace } from "lucide-react";
import type { NotificationOut as Notification } from "@/shared/api/generated/model";
import { startOfToday } from "@/shared/lib/format";

/** S4 groups: today's items, then everything older. Empty groups are dropped. */
export function groupByDay(
  items: Notification[],
  now: Date = new Date(),
): { label: string; items: Notification[] }[] {
  const midnight = startOfToday(now);
  const today = items.filter((item) => new Date(item.created_at).getTime() >= midnight);
  const earlier = items.filter((item) => new Date(item.created_at).getTime() < midnight);
  return [
    { label: "Hari ini", items: today },
    { label: "Sebelumnya", items: earlier },
  ].filter((group) => group.items.length > 0);
}

// The API sends no notification type, so the icon follows the page the notification opens.
const ICONS: [string, LucideIcon][] = [
  ["/app/attendance", ScanFace],
  ["/app/time", CalendarDays],
  ["/app/approvals", CalendarDays],
  ["/app/payroll", ReceiptText],
];

export function notificationIcon(target: string): LucideIcon {
  return ICONS.find(([prefix]) => target.startsWith(prefix))?.[1] ?? Bell;
}
