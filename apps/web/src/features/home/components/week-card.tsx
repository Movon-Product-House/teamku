import type { WeekOut } from "@/shared/api/generated/model";
import { cn } from "@/shared/lib/cn";
import { weekBars } from "../home";

const TONES = {
  actual: "bg-foreground",
  late: "bg-warning",
  leave: "bg-info-muted",
} as const;

const LEGEND = [
  ["Aktual", TONES.actual],
  ["Target", "bg-secondary"],
  ["Terlambat", TONES.late],
  ["Cuti", TONES.leave],
] as const;

/** D1 "Jam kerja minggu ini": actual hours per weekday next to the daily target. */
export function WeekCard({ week }: { week: WeekOut }) {
  const bars = weekBars(week);
  return (
    <section aria-labelledby="week-title" className="flex flex-col gap-5 rounded-card bg-card p-7">
      <div>
        <h2 id="week-title" className="text-heading">
          Jam kerja minggu ini
        </h2>
        <p className="text-caption text-muted-foreground">
          Dibanding target {week.target_hours} jam per hari
        </p>
      </div>
      <ul className="flex h-40 items-end justify-between gap-3 border-border border-b pb-3">
        {bars.map((bar) => (
          <li key={bar.date} className="flex h-full flex-1 flex-col items-center gap-2">
            <div className="flex w-full flex-1 items-end justify-center gap-1">
              <span
                className={cn("w-3 rounded-full", TONES[bar.tone])}
                style={{ height: `${bar.actual}%` }}
              />
              <span
                className="w-3 rounded-full bg-secondary"
                style={{ height: `${bar.target}%` }}
              />
            </div>
            <span className="text-caption text-faint-foreground">{bar.label}</span>
            <span className="sr-only">
              {bar.tone === "leave"
                ? "cuti"
                : `${bar.hours.toLocaleString("id-ID")} jam${bar.tone === "late" ? ", terlambat" : ""}`}
            </span>
          </li>
        ))}
      </ul>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-caption text-muted-foreground" aria-hidden>
        {LEGEND.map(([label, color]) => (
          <li key={label} className="flex items-center gap-1.5">
            <span className={cn("size-2 rounded-full", color)} />
            {label}
          </li>
        ))}
      </ul>
    </section>
  );
}
