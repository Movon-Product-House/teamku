import { describe, expect, it } from "vitest";
import type { CheckOutOut, SessionOut, TodayOut } from "@/shared/api/generated/model";
import {
  checkOutMessage,
  formatDuration,
  greeting,
  timelineSlots,
  todaySpans,
  weekBars,
  workedMs,
} from "./home";

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
      sessions_today: [],
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
      sessions_today: [],
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
    const slots = timelineSlots([{ start: at(8, 52), end: at(12, 10) }], 10);
    expect(slots).toEqual([true, true, true, true, true, false, false, false, false, false]);
  });

  it("reports the session and the day total after check-out", () => {
    expect(
      checkOutMessage({
        id: "s",
        checked_out_at: "",
        effective_hours: 1.5,
        total_hours_today: 4.25,
      }),
    ).toBe("Sesi ini 1j 30m · total hari ini 4j 15m.");
    // An API deployed behind the web sends no total.
    const olderApi = { id: "s", checked_out_at: "", effective_hours: 0.25 } as CheckOutOut;
    expect(checkOutMessage(olderApi)).toBe("Sesi ini 15m.");
    // 50 minutes arrives as 0.83 hours and must not read as 49m.
    expect(
      checkOutMessage({
        id: "s",
        checked_out_at: "",
        effective_hours: 0.83,
        total_hours_today: 0.83,
      }),
    ).toBe("Sesi ini 50m · total hari ini 50m.");
  });

  it("names the check-in day in the toast when a night shift ends after midnight WIB", () => {
    // Wednesday 20:00 WIB to Thursday 02:00 WIB.
    const nightShift = {
      id: "s",
      checked_out_at: "2026-10-21T19:00:00Z",
      effective_hours: 6,
      total_hours_today: 7,
    };
    expect(checkOutMessage(nightShift, "2026-10-21T13:00:00Z")).toBe(
      "Sesi ini 6j 0m · total hari Rabu 7j 0m.",
    );
    // Same WIB day: still "hari ini".
    expect(checkOutMessage(nightShift, "2026-10-21T18:00:00Z")).toBe(
      "Sesi ini 6j 0m · total hari ini 7j 0m.",
    );
  });

  it("turns today's sessions into timeline spans, the open one running until now", () => {
    const today: TodayOut = {
      state: "checked_in",
      session: session(at(13).toISOString(), null),
      pending_reverification: null,
      is_remote: false,
      closed_hours_today: 1,
      sessions_today: [
        { checked_in_at: at(8).toISOString(), checked_out_at: at(9).toISOString() },
        { checked_in_at: at(13).toISOString(), checked_out_at: null },
      ],
    };
    expect(todaySpans(today, at(14))).toEqual([
      { start: at(8), end: at(9) },
      { start: at(13), end: at(14) },
    ]);
    // An API deployed behind the web sends no sessions_today: the latest session stands in.
    const { sessions_today: _, ...olderApi } = today;
    expect(todaySpans(olderApi as TodayOut, at(14))).toEqual([{ start: at(13), end: at(14) }]);
    expect(todaySpans({ ...olderApi, session: null } as TodayOut, at(14))).toEqual([]);
  });

  it("fills the timeline for every session today, leaving the gaps empty", () => {
    const slots = timelineSlots(
      [
        { start: at(8), end: at(9) },
        { start: at(13, 30), end: at(15) },
      ],
      10,
    );
    expect(slots).toEqual([true, false, false, false, false, true, true, false, false, false]);
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
