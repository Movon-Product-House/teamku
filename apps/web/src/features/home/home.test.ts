import { describe, expect, it } from "vitest";
import type { SessionOut, TodayOut } from "@/shared/api/generated/model";
import { formatDuration, greeting, timelineSlots, weekBars, workedMs } from "./home";

const at = (hour: number, minute = 0) => new Date(2026, 8, 29, hour, minute);
const session = (checked_in_at: string, checked_out_at: string | null): SessionOut => ({
  id: "s",
  checked_in_at,
  checked_out_at,
  anomaly: null,
  agenda_count: 0,
  agenda: [],
  summary: null,
});

describe("home", () => {
  it("greets by time of day", () => {
    expect(greeting(at(8))).toBe("Selamat pagi");
    expect(greeting(at(12))).toBe("Selamat siang");
    expect(greeting(at(16))).toBe("Selamat sore");
    expect(greeting(at(20))).toBe("Selamat malam");
  });

  it("sums the closed sessions of today with the open one", () => {
    const today = (state: TodayOut["state"], checked_out_at: string | null): TodayOut => ({
      state,
      session: session(at(13).toISOString(), checked_out_at),
      pending_reverification: null,
      is_remote: false,
      closed_hours_today: 1.5,
    });
    expect(workedMs(today("checked_in", null), at(14))).toBe(2.5 * 3_600_000);
    expect(workedMs(today("completed", at(14).toISOString()), at(18))).toBe(1.5 * 3_600_000);
  });

  it("never lets the open session go negative or past midnight WIB", () => {
    const open = (checked_in_at: string): TodayOut => ({
      state: "checked_in",
      session: session(checked_in_at, null),
      pending_reverification: null,
      is_remote: false,
      closed_hours_today: 1,
    });
    // Device clock two minutes behind the server.
    expect(workedMs(open("2026-09-29T06:02:00Z"), new Date("2026-09-29T06:00:00Z"))).toBe(
      3_600_000,
    );
    // 23.00 WIB check-in, 01.00 WIB now: counts up to 00.00 WIB only.
    expect(workedMs(open("2026-09-29T16:00:00Z"), new Date("2026-09-29T18:00:00Z"))).toBe(
      2 * 3_600_000,
    );
  });

  it("formats a work duration as hours and minutes", () => {
    expect(formatDuration((3 * 60 + 18) * 60_000)).toBe("3j 18m");
    expect(formatDuration(18 * 60_000)).toBe("18m");
    expect(formatDuration(-5)).toBe("0m");
  });

  it("fills the timeline slots between check-in and now", () => {
    // 10 slots of one hour from 08.00 to 18.00.
    const slots = timelineSlots(at(8, 52), at(12, 10), 10);
    expect(slots).toEqual([true, true, true, true, true, false, false, false, false, false]);
  });

  it("scales the week to the target and colours late and leave days", () => {
    const bars = weekBars({
      target_hours: 8,
      days: [
        { date: "2026-09-28", hours: 8, late: false, on_leave: false },
        { date: "2026-09-29", hours: 2, late: true, on_leave: false },
        { date: "2026-09-30", hours: 0, late: false, on_leave: true },
        { date: "2026-10-01", hours: 10, late: false, on_leave: false },
        { date: "2026-10-02", hours: 0, late: false, on_leave: false },
      ],
    });
    expect(bars.map((bar) => bar.label)).toEqual(["Sen", "Sel", "Rab", "Kam", "Jum"]);
    expect(bars.map((bar) => bar.tone)).toEqual(["actual", "late", "leave", "actual", "actual"]);
    expect(bars[0]).toMatchObject({ actual: 80, target: 80 });
    expect(bars[2].actual).toBe(80);
    expect(bars[3].actual).toBe(100);
    expect(bars[4].actual).toBe(0);
  });
});
