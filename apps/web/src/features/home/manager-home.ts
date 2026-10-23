import type { ApprovalOut, DashboardOut } from "@/shared/api/generated/model";

const clock = new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit" });
const dayMonth = new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "short" });
const day = new Intl.DateTimeFormat("id-ID", { day: "numeric" });
const asDate = (iso: string) => new Date(`${iso}T00:00:00`);
const firstName = (name: string) => name.split(" ")[0];

export const APPROVALS_HREF = "/app/approvals";
export const PEOPLE_HREF = "/app/people";

/** "6 Okt", "6–8 Okt", "30 Sep–2 Okt". Dates are "YYYY-MM-DD", read as local dates. */
export function dateRange(start: string, end: string): string {
  const [from, to] = [asDate(start), asDate(end)];
  if (start === end) return dayMonth.format(from);
  if (from.getMonth() === to.getMonth()) return `${day.format(from)}–${dayMonth.format(to)}`;
  return `${dayMonth.format(from)}–${dayMonth.format(to)}`;
}

/** Local "YYYY-MM-DD" of `now`, comparable with the API's leave dates. */
export function isoDay(now: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** Pending leave requests, earliest start first. */
export function pendingLeave(items: ApprovalOut[]): ApprovalOut[] {
  return items
    .filter((item) => item.status === "pending")
    .sort((a, b) => a.start.localeCompare(b.start));
}

export function pendingBanner(pending: ApprovalOut[]): string | null {
  const first = pending[0];
  if (!first) return null;
  return `${pending.length} permohonan cuti menunggu keputusanmu. Paling awal: ${first.employee_name}, ${dateRange(first.start, first.end)}.`;
}

export type Tone = "success" | "warning" | "info" | "neutral";
export type Segment = { label: string; count: number; tone: Tone };

/** The composition bar under "N / M hadir": on time, late, on leave, not checked in. */
export function composition(dashboard: DashboardOut): Segment[] {
  return [
    { label: "Tepat waktu", count: dashboard.present - dashboard.late, tone: "success" },
    { label: "Terlambat", count: dashboard.late, tone: "warning" },
    { label: "Cuti", count: dashboard.on_leave, tone: "info" },
    { label: "Belum check-in", count: dashboard.absent, tone: "neutral" },
  ];
}

export type WatchRow = {
  employeeId: string;
  name: string;
  title: string;
  status: "Terlambat" | "Belum check-in" | "Cuti";
  tone: Tone;
  detail: string;
};

/** Members worth a look today: late, not checked in yet, then on leave. */
export function watchList(dashboard: DashboardOut, today: string): WatchRow[] {
  const flagged = (kind: "late" | "not_checked_in") =>
    dashboard.attention.filter((item) => item.kind === kind);
  return [
    ...flagged("late").map((item) => ({
      employeeId: item.employee_id,
      name: item.employee,
      title: item.title,
      status: "Terlambat" as const,
      tone: "warning" as const,
      detail: item.at ? clock.format(new Date(item.at)) : "—",
    })),
    ...flagged("not_checked_in").map((item) => ({
      employeeId: item.employee_id,
      name: item.employee,
      title: item.title,
      status: "Belum check-in" as const,
      tone: "neutral" as const,
      detail: "—",
    })),
    ...dashboard.team_leave
      .filter((item) => item.status === "approved" && item.start_date <= today)
      .map((item) => ({
        employeeId: item.employee_id,
        name: item.employee,
        title: item.title,
        status: "Cuti" as const,
        tone: "info" as const,
        detail: `s.d. ${dayMonth.format(asDate(item.end_date))}`,
      })),
  ];
}

export type ActionItem = {
  key: string;
  kind: "leave" | "outside_geofence" | "missed_reverify" | "not_checked_in";
  title: string;
  detail: string;
  href: string;
  cta: string;
};

/** "Rina, Andi, Dewi" or "Rina, Andi, Dewi +2". */
function names(list: string[]): string {
  const shown = list.slice(0, 3).map(firstName).join(", ");
  return list.length > 3 ? `${shown} +${list.length - 3}` : shown;
}

/** "Perlu tindakan": everything that needs the manager, most urgent first. */
export function actionItems(dashboard: DashboardOut, pending: ApprovalOut[]): ActionItem[] {
  const items: ActionItem[] = [];
  if (pending.length)
    items.push({
      key: "leave",
      kind: "leave",
      title: `${pending.length} cuti menunggu`,
      detail: `${names(pending.map((item) => item.employee_name))} · paling awal ${dayMonth.format(asDate(pending[0].start))}`,
      href: APPROVALS_HREF,
      cta: "Tinjau",
    });
  for (const row of dashboard.attendance.filter((item) => item.anomaly === "outside_geofence"))
    items.push({
      key: `geofence-${row.employee_id}-${row.checked_in_at}`,
      kind: "outside_geofence",
      title: "Lokasi di luar radius",
      detail: `${row.employee} · check-in ${clock.format(new Date(row.checked_in_at))}`,
      href: `${PEOPLE_HREF}/${row.employee_id}`,
      cta: "Lihat lokasi",
    });
  for (const item of dashboard.attention.filter((entry) => entry.kind === "missed_reverify"))
    items.push({
      key: `reverify-${item.employee_id}`,
      kind: "missed_reverify",
      title: "Re-verifikasi terlewat",
      detail: item.at
        ? `${item.employee} · terlewat ${clock.format(new Date(item.at))}`
        : item.employee,
      href: `${PEOPLE_HREF}/${item.employee_id}`,
      cta: "Lihat",
    });
  const absent = dashboard.attention.filter((item) => item.kind === "not_checked_in");
  if (absent.length)
    items.push({
      key: "not-checked-in",
      kind: "not_checked_in",
      title: absent.length > 1 ? `${absent.length} belum check-in` : "Belum check-in",
      detail: `${absent.length > 1 ? names(absent.map((item) => item.employee)) : absent[0].employee} · shift mulai ${dashboard.work_start_time.replace(":", ".")}`,
      href: absent.length > 1 ? PEOPLE_HREF : `${PEOPLE_HREF}/${absent[0].employee_id}`,
      cta: "Lihat",
    });
  return items;
}
