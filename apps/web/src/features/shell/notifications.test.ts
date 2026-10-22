import { Bell, CalendarDays, ReceiptText, ScanFace } from "lucide-react";
import { describe, expect, it } from "vitest";
import type { NotificationOut } from "@/shared/api/generated/model";
import { groupByDay, notificationIcon } from "./notifications";

const item = (id: string, created_at: string): NotificationOut => ({
  id,
  user_id: "u1",
  title: id,
  detail: "",
  target: "/app/overview",
  created_at,
  read: false,
});

describe("groupByDay", () => {
  const now = new Date(2026, 9, 21, 15, 0);

  it("splits at local midnight into Hari ini and Sebelumnya, keeping order", () => {
    const groups = groupByDay(
      [
        item("a", new Date(2026, 9, 21, 11, 30).toISOString()),
        item("b", new Date(2026, 9, 21, 0, 0).toISOString()),
        item("c", new Date(2026, 9, 20, 23, 59).toISOString()),
      ],
      now,
    );
    expect(groups.map((group) => [group.label, group.items.map((it) => it.id)])).toEqual([
      ["Hari ini", ["a", "b"]],
      ["Sebelumnya", ["c"]],
    ]);
  });

  it("drops an empty group", () => {
    const groups = groupByDay([item("c", new Date(2026, 9, 1).toISOString())], now);
    expect(groups.map((group) => group.label)).toEqual(["Sebelumnya"]);
  });
});

describe("notificationIcon", () => {
  it("picks the icon from the target page", () => {
    expect(notificationIcon("/app/attendance/today")).toBe(ScanFace);
    expect(notificationIcon("/app/time/time-off")).toBe(CalendarDays);
    expect(notificationIcon("/app/approvals")).toBe(CalendarDays);
    expect(notificationIcon("/app/payroll/payslips")).toBe(ReceiptText);
    expect(notificationIcon("/app/overview")).toBe(Bell);
  });
});
