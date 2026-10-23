import { describe, expect, it } from "vitest";
import type {
  ApprovalOut,
  DashboardAttentionOut,
  DashboardOut,
} from "@/shared/api/generated/model";
import {
  actionItems,
  composition,
  dateRange,
  isoDay,
  pendingBanner,
  pendingLeave,
  watchList,
} from "./manager-home";

// Only the fields these functions read; current_user and the counters stay out of the way.
const dashboard = (overrides: Partial<DashboardOut> = {}): DashboardOut =>
  ({
    present: 10,
    late: 2,
    on_leave: 1,
    absent: 1,
    work_start_time: "09:00",
    attendance: [],
    attention: [],
    agenda: [],
    team_leave: [],
    ...overrides,
  }) as DashboardOut;
const flag = (
  employee: string,
  kind: DashboardAttentionOut["kind"],
  at: string | null = null,
): DashboardAttentionOut => ({
  employee_id: employee.toLowerCase(),
  employee,
  title: "Sales Executive",
  kind,
  at,
});
const request = (employee_name: string, start: string, end: string, status = "pending") =>
  ({ employee_id: employee_name.toLowerCase(), employee_name, start, end, status }) as ApprovalOut;
const pad = (value: number) => String(value).padStart(2, "0");
// API moments are WIB whatever zone the browser runs in.
const wib = (hour: number, minute: number, day = 29) =>
  `2026-09-${day}T${pad(hour)}:${pad(minute)}:00+07:00`;
const SELF = "budi hartono";

describe("manager home", () => {
  it("writes leave ranges compactly", () => {
    expect(dateRange("2026-10-06", "2026-10-08")).toBe("6–8 Okt");
    expect(dateRange("2026-09-30", "2026-10-02")).toBe("30 Sep–2 Okt");
    expect(dateRange("2026-10-06", "2026-10-06")).toBe("6 Okt");
    expect(isoDay(new Date("2026-09-09T23:30:00+07:00"))).toBe("2026-09-09");
    // 01.30 WIB is already the next day, even where the browser clock still says the 9th.
    expect(isoDay(new Date("2026-09-09T18:30:00Z"))).toBe("2026-09-10");
  });

  it("names the earliest pending request in the banner, nothing when none wait", () => {
    const pending = pendingLeave(
      [
        request("Andi Pratama", "2026-10-20", "2026-10-20"),
        request("Sari Wulan", "2026-10-01", "2026-10-02", "approved"),
        request("Rina Sari", "2026-10-06", "2026-10-08"),
        // The manager's own request goes to HR, never to their own queue.
        request("Budi Hartono", "2026-10-02", "2026-10-02"),
      ],
      SELF,
    );
    expect(pending.map((item) => item.employee_name)).toEqual(["Rina Sari", "Andi Pratama"]);
    expect(pendingBanner(pending)).toBe(
      "2 permohonan cuti menunggu keputusanmu. Paling awal: Rina Sari, 6–8 Okt.",
    );
    expect(pendingBanner([])).toBeNull();
  });

  it("splits the present count into on time and late", () => {
    expect(composition(dashboard()).map((item) => [item.label, item.count])).toEqual([
      ["Tepat waktu", 8],
      ["Terlambat", 2],
      ["Cuti", 1],
      ["Belum check-in", 1],
    ]);
  });

  it("lists late members, missing check-ins, open sessions, then leave that has started", () => {
    const rows = watchList(
      dashboard({
        attention: [
          flag("Fajar Hidayat", "open_session", wib(22, 0, 27)),
          flag("Dewi Lestari", "not_checked_in"),
          flag("Andi Pratama", "late", wib(9, 21)),
          flag("Joko Santoso", "missed_reverify", wib(12, 45)),
        ],
        team_leave: [
          {
            employee_id: "sari",
            employee: "Sari Wulan",
            title: "Sales Admin",
            start_date: "2026-09-28",
            end_date: "2026-09-30",
            status: "approved",
          },
          {
            employee_id: "rina",
            employee: "Rina Sari",
            title: "Staf Sales",
            start_date: "2026-10-06",
            end_date: "2026-10-08",
            status: "approved",
          },
        ],
      }),
      "2026-09-29",
    );
    expect(rows.map((row) => [row.name, row.status, row.detail])).toEqual([
      ["Andi Pratama", "Terlambat", "09.21"],
      ["Dewi Lestari", "Belum check-in", "—"],
      ["Fajar Hidayat", "Sesi terbuka", "sejak 27 Sep"],
      ["Sari Wulan", "Cuti", "s.d. 30 Sep"],
    ]);
  });

  it("gathers what needs the manager, most urgent first", () => {
    const items = actionItems(
      dashboard({
        attendance: [
          {
            employee_id: "andi",
            employee: "Andi Pratama",
            department: "Sales",
            checked_in_at: wib(9, 21),
            checked_out_at: null,
            anomaly: "outside_geofence",
          },
        ],
        attention: [
          flag("Joko Santoso", "missed_reverify", wib(12, 45)),
          flag("Fajar Hidayat", "open_session", wib(22, 0, 28)),
          flag("Dewi Lestari", "not_checked_in"),
        ],
      }),
      pendingLeave(
        [
          request("Rina Sari", "2026-10-06", "2026-10-08"),
          request("Andi Pratama", "2026-10-20", "2026-10-20"),
          request("Dewi Lestari", "2026-10-21", "2026-10-22"),
          request("Maya Kusuma", "2026-10-23", "2026-10-23"),
        ],
        SELF,
      ),
    );
    expect(items.map((item) => [item.title, item.detail, item.href])).toEqual([
      ["4 cuti menunggu", "Rina, Andi, Dewi +1 · paling awal 6 Okt", "/app/approvals"],
      ["Lokasi di luar radius", "Andi Pratama · check-in 09.21", "/app/people/andi"],
      ["Re-verifikasi terlewat", "Joko Santoso · terlewat 12.45", "/app/people/joko santoso"],
      ["Sesi belum ditutup", "Fajar Hidayat · check-in 28 Sep 22.00", "/app/people/fajar hidayat"],
      ["Belum check-in", "Dewi Lestari · shift mulai 09.00", "/app/people/dewi lestari"],
    ]);
  });

  it("groups several missing check-ins into one item", () => {
    const items = actionItems(
      dashboard({
        attention: [
          flag("Dewi Lestari", "not_checked_in"),
          flag("Fajar Hidayat", "not_checked_in"),
        ],
      }),
      [],
    );
    expect(items.map((item) => [item.title, item.detail, item.href])).toEqual([
      ["2 belum check-in", "Dewi, Fajar · shift mulai 09.00", "/app/people"],
    ]);
  });
});
