import type { CheckOutOut, TodayOut, WeekOut } from "@/shared/api/generated/model";

export function greeting(now: Date): string {
  const hour = now.getHours();
  if (hour < 11) return "Selamat pagi";
  if (hour < 15) return "Selamat siang";
  if (hour < 18) return "Selamat sore";
  return "Selamat malam";
}

const HOUR_MS = 3_600_000;
const DAY_MS = 24 * HOUR_MS;
const WIB_OFFSET_MS = 7 * HOUR_MS; // Asia/Jakarta has no DST.

/** Every session today counts: the closed ones plus the open one, capped like the API's worked_hours. */
export function workedMs(today: TodayOut, now: Date): number {
  const closed = (today.closed_hours_today ?? 0) * HOUR_MS;
  if (today.state !== "checked_in" || !today.session) return closed;
  const start = new Date(today.session.checked_in_at).getTime();
  const dayEnd = Math.floor((start + WIB_OFFSET_MS) / DAY_MS) * DAY_MS + DAY_MS - WIB_OFFSET_MS;
  // max(0): a device clock behind the server must not eat into the closed hours.
  return closed + Math.max(0, Math.min(now.getTime(), dayEnd) - start);
}

/** 198 minutes → "3j 18m"; under an hour → "18m". */
export function formatDuration(ms: number): string {
  const minutes = Math.max(0, Math.floor(ms / 60_000));
  const hours = Math.floor(minutes / 60);
  return hours ? `${hours}j ${minutes % 60}m` : `${minutes}m`;
}

/** Check-out toast: this session, then the whole day. */
export function checkOutMessage(result: CheckOutOut): string {
  const session = formatDuration(result.effective_hours * HOUR_MS);
  // The web can deploy ahead of the API, which then sends no total.
  if (result.total_hours_today == null) return `Sesi ini ${session}.`;
  const total = formatDuration(result.total_hours_today * HOUR_MS);
  return `Sesi ini ${session} · total hari ini ${total}.`;
}

export type Span = { start: Date; end: Date };

/** Every session today as a span; the open one runs until now. */
export function todaySpans(today: TodayOut, now: Date): Span[] {
  // The web can deploy ahead of the API, which then sends no sessions_today.
  const sessions = today.sessions_today ?? (today.session ? [today.session] : []);
  return sessions.map((item) => ({
    start: new Date(item.checked_in_at),
    end: item.checked_out_at ? new Date(item.checked_out_at) : now,
  }));
}

/** Slots from 08.00 to 18.00 on the first span's day; a slot is filled when it overlaps any span. */
export function timelineSlots(spans: Span[], count = 48, from = 8, to = 18): boolean[] {
  const first = spans[0]?.start ?? new Date();
  const day = new Date(first.getFullYear(), first.getMonth(), first.getDate()).getTime();
  const size = ((to - from) * HOUR_MS) / count;
  return Array.from({ length: count }, (_, index) => {
    const slotStart = day + from * HOUR_MS + index * size;
    return spans.some(
      ({ start, end }) => slotStart < end.getTime() && slotStart + size > start.getTime(),
    );
  });
}

const DAY_LABELS = ["Sen", "Sel", "Rab", "Kam", "Jum"];

export type WeekBar = {
  date: string;
  label: string;
  hours: number;
  /** Bar heights as a percentage of the tallest value (target or longest day). */
  actual: number;
  target: number;
  tone: "actual" | "late" | "leave";
};

export function weekBars(week: WeekOut): WeekBar[] {
  const scale = Math.max(week.target_hours * 1.25, ...week.days.map((day) => day.hours));
  const target = (week.target_hours / scale) * 100;
  return week.days.map((day, index) => ({
    date: day.date,
    label: DAY_LABELS[index] ?? day.date,
    hours: day.hours,
    actual: day.on_leave ? target : (day.hours / scale) * 100,
    target,
    tone: day.on_leave ? "leave" : day.late ? "late" : "actual",
  }));
}
