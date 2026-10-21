import type { Today, Week } from "./types";

export function greeting(now: Date): string {
  const hour = now.getHours();
  if (hour < 11) return "Selamat pagi";
  if (hour < 15) return "Selamat siang";
  if (hour < 18) return "Selamat sore";
  return "Selamat malam";
}

/** Every session today counts: the closed ones plus the open one up to now. */
export function workedMs(today: Today, now: Date): number {
  // ?? 0: an older API without the field must not render "NaNm".
  const closed = (today.closed_hours_today ?? 0) * 3_600_000;
  const open =
    today.state === "checked_in" && today.session
      ? now.getTime() - new Date(today.session.checked_in_at).getTime()
      : 0;
  return closed + open;
}

/** 198 minutes → "3j 18m"; under an hour → "18m". */
export function formatDuration(ms: number): string {
  const minutes = Math.max(0, Math.floor(ms / 60_000));
  const hours = Math.floor(minutes / 60);
  return hours ? `${hours}j ${minutes % 60}m` : `${minutes}m`;
}

/** Slots from 08.00 to 18.00; a slot is filled when it overlaps the worked span. */
export function timelineSlots(start: Date, end: Date, count = 48, from = 8, to = 18): boolean[] {
  const day = new Date(start.getFullYear(), start.getMonth(), start.getDate()).getTime();
  const size = ((to - from) * 3_600_000) / count;
  return Array.from({ length: count }, (_, index) => {
    const slotStart = day + from * 3_600_000 + index * size;
    return slotStart < end.getTime() && slotStart + size > start.getTime();
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

export function weekBars(week: Week): WeekBar[] {
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
