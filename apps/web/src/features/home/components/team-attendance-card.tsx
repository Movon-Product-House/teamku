import Link from "next/link";
import type { DashboardOut } from "@/shared/api/generated/model";
import { cn } from "@/shared/lib/cn";
import { initials } from "@/shared/lib/format";
import { Badge } from "@/shared/ui/badge";
import { composition, PEOPLE_HREF, type Tone, watchList } from "../manager-home";

const segmentFill: Record<Tone, string> = {
  success: "bg-success",
  warning: "bg-warning",
  info: "bg-info",
  neutral: "bg-secondary",
};

/** M1 "Kehadiran tim": present / headcount, the composition bar and who needs a look. */
export function TeamAttendanceCard({
  dashboard,
  today,
}: {
  dashboard: DashboardOut;
  today: string;
}) {
  const segments = composition(dashboard);
  const rows = watchList(dashboard, today);
  return (
    <section
      aria-labelledby="team-attendance"
      className="flex flex-col gap-5 rounded-card bg-card p-5 md:p-7"
    >
      <div className="flex flex-col gap-1">
        <h2 id="team-attendance" className="flex items-end gap-2.5 font-display">
          <span className="text-title lg:text-display">{dashboard.present}</span>
          <span className="pb-1 text-faint-foreground text-title-xs lg:text-title-sm">
            / {dashboard.headcount}
          </span>
          <span className="sr-only">anggota tim hadir</span>
        </h2>
        <p className="text-body text-faint-foreground">
          Anggota tim hadir hari ini · {dashboard.attendance_rate}%
        </p>
      </div>

      {dashboard.headcount > 0 && (
        <div className="flex h-3.5 gap-1" aria-hidden>
          {segments.map(
            (segment) =>
              segment.count > 0 && (
                <span
                  key={segment.label}
                  className={cn("rounded-xs", segmentFill[segment.tone])}
                  style={{ flexGrow: segment.count }}
                />
              ),
          )}
        </div>
      )}
      <ul className="flex flex-wrap gap-x-6 gap-y-2">
        {segments.map((segment) => (
          <li key={segment.label}>
            <Badge tone={segment.tone} variant="plain">
              {segment.label} {segment.count}
            </Badge>
          </li>
        ))}
      </ul>

      {rows.length === 0 ? (
        <p className="border-border border-t pt-4 text-body text-muted-foreground">
          Semua anggota tim tepat waktu hari ini.
        </p>
      ) : (
        <ul className="flex flex-col border-border border-t pt-2">
          {rows.map((row) => (
            <li
              key={`${row.status}-${row.employeeId}`}
              className="border-border border-b last:border-b-0"
            >
              <Link
                href={`${PEOPLE_HREF}/${row.employeeId}`}
                className="flex items-center gap-3 py-3 outline-none hover:bg-secondary/60 focus-visible:outline-2 focus-visible:outline-ring"
              >
                <span
                  className="flex size-9 shrink-0 items-center justify-center rounded-full bg-secondary font-bold text-caption text-muted-foreground"
                  aria-hidden
                >
                  {initials(row.name)}
                </span>
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate font-semibold text-sm">{row.name}</span>
                  <span className="truncate text-faint-foreground text-xs">{row.title}</span>
                </span>
                <Badge tone={row.tone} variant="plain" className="w-32 max-sm:w-auto">
                  {row.status}
                </Badge>
                <span className="w-20 text-right text-caption text-muted-foreground max-sm:hidden">
                  {row.detail}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
