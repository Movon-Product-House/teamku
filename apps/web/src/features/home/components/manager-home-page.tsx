"use client";

import { Inbox, LogIn, LogOut, Sparkles, Users } from "lucide-react";
import Link from "next/link";
import { useGetAttendanceToday, useGetDashboard } from "@/shared/api/generated";
import type { ApprovalOut, DashboardOut, MeOut, TodayOut } from "@/shared/api/generated/model";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { usePendingLeave } from "../api";
import { formatDuration, greeting, workedMs } from "../home";
import {
  APPROVALS_HREF,
  actionItems,
  dateRange,
  isoDay,
  PEOPLE_HREF,
  pendingBanner,
} from "../manager-home";
import { Loaded } from "./loaded";
import { ManagerActions } from "./manager-actions";
import { TeamAttendanceCard } from "./team-attendance-card";
import { ATTENDANCE_HREF } from "./today-card";

const ASK_HREF = "/app/ask-teamku";
const longDate = new Intl.DateTimeFormat("id-ID", {
  weekday: "long",
  day: "numeric",
  month: "long",
  timeZone: "Asia/Jakarta",
});

/** M1: Beranda for a Manager. */
export function ManagerHomePage({ user }: { user: MeOut["user"] }) {
  const dashboard = useGetDashboard();
  const approvals = usePendingLeave(user.id);
  const today = useGetAttendanceToday();
  const now = new Date();

  return (
    <div data-surface="v2" className="mx-auto flex w-full max-w-6xl flex-col gap-4 pb-5 lg:gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <h1 className="font-display text-title-sm lg:text-title">
            {greeting(now)}, {user.name.split(" ")[0]}
          </h1>
          <p className="text-body text-faint-foreground">
            {longDate.format(now)} · Manager {user.department}
            {dashboard.data && ` · ${dashboard.data.headcount} anggota tim`}
          </p>
        </div>
        <div className="flex gap-2.5 max-lg:hidden">
          <Button asChild variant="secondary">
            <Link href={PEOPLE_HREF}>
              <Users />
              Tim Saya
            </Link>
          </Button>
          <Button asChild>
            <Link href={ASK_HREF}>
              <Sparkles />
              Tanya Teamku
            </Link>
          </Button>
        </div>
      </header>

      <Loaded query={approvals} label="Cuti menunggu" className="min-h-16 rounded-tile">
        {(pending) => <PendingBanner pending={pending} />}
      </Loaded>

      <Loaded query={dashboard} label="Ringkasan tim" className="min-h-96">
        {(data) => (
          <>
            <div className="grid gap-4 lg:grid-cols-[1fr_400px] lg:items-start lg:gap-6">
              <TeamAttendanceCard dashboard={data} today={isoDay(now)} />
              <ManagerActions items={actionItems(data, approvals.data ?? [])} />
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-[1fr_320px_320px] lg:gap-6">
              <Loaded query={today} label="Sesi saya">
                {(session) => <MySessionCard today={session} now={now} />}
              </Loaded>
              <TeamAgendaCard dashboard={data} />
              <TeamLeaveCard dashboard={data} />
            </div>
          </>
        )}
      </Loaded>
    </div>
  );
}

function PendingBanner({ pending }: { pending: ApprovalOut[] }) {
  const banner = pendingBanner(pending);
  if (!banner) return null;
  return (
    <div className="flex flex-wrap items-center gap-3.5 rounded-tile bg-card px-5 py-4">
      <span className="flex size-7 shrink-0 items-center justify-center rounded-control bg-brand">
        <Inbox className="size-4 text-primary-foreground" aria-hidden />
      </span>
      <p className="min-w-0 flex-1 basis-60 text-body">{banner}</p>
      <Button asChild size="sm">
        <Link href={APPROVALS_HREF}>Tinjau sekarang</Link>
      </Button>
    </div>
  );
}

function MySessionCard({ today, now }: { today: TodayOut; now: Date }) {
  const working = today.state === "checked_in";
  const started = today.state !== "not_checked_in";
  return (
    <section
      aria-labelledby="my-session"
      className="flex items-center justify-between gap-2 rounded-card bg-card px-7 py-6"
    >
      <div className="flex flex-col gap-1">
        <h2 id="my-session" className="text-body text-faint-foreground">
          Sesi saya
        </h2>
        <p className="font-display text-title-sm">
          {started ? formatDuration(workedMs(today, now)) : "—"}
        </p>
        <Badge tone={working ? "success" : "neutral"} variant="plain">
          {working ? "Sedang bekerja" : started ? "Hari kerja selesai" : "Belum check-in"}
        </Badge>
      </div>
      {(working || !started) && (
        <Button asChild size="sm" variant="outline">
          <Link href={ATTENDANCE_HREF}>
            {working ? <LogOut /> : <LogIn />}
            {working ? "Check-out" : "Check-in"}
          </Link>
        </Button>
      )}
    </section>
  );
}

function TeamAgendaCard({ dashboard }: { dashboard: DashboardOut }) {
  const { agenda_completed: done, agenda_total: total } = dashboard;
  return (
    <section
      aria-labelledby="team-agenda"
      className="flex flex-col gap-2 rounded-card bg-card px-7 py-6"
    >
      <h2 id="team-agenda" className="text-body text-faint-foreground">
        Agenda tim hari ini
      </h2>
      {total === 0 ? (
        <p className="text-body text-muted-foreground">Belum ada agenda tim hari ini.</p>
      ) : (
        <>
          <p className="flex items-end gap-2 font-display">
            <span className="text-title-sm">{done}</span>
            <span className="text-faint-foreground text-title-xs">/ {total}</span>
            <span className="sr-only">item selesai</span>
          </p>
          <div className="h-1.5 rounded-full bg-secondary" aria-hidden>
            <div
              className="h-full rounded-full bg-foreground"
              style={{ width: `${(done / total) * 100}%` }}
            />
          </div>
        </>
      )}
    </section>
  );
}

function TeamLeaveCard({ dashboard }: { dashboard: DashboardOut }) {
  return (
    <section
      aria-labelledby="team-leave"
      className="flex flex-col gap-2.5 rounded-card bg-card px-7 py-6"
    >
      <h2 id="team-leave" className="text-body text-faint-foreground">
        Cuti tim 2 minggu ke depan
      </h2>
      {dashboard.team_leave.length === 0 ? (
        <p className="text-body text-muted-foreground">Tidak ada cuti tim.</p>
      ) : (
        <ul className="flex flex-col gap-2.5">
          {dashboard.team_leave.map((item) => (
            <li
              key={`${item.employee_id}-${item.start_date}-${item.status}`}
              className="flex justify-between gap-3"
            >
              <span className="truncate text-body">{item.employee}</span>
              <span className="shrink-0 text-caption text-faint-foreground">
                {dateRange(item.start_date, item.end_date)}
                {item.status === "pending" && " · menunggu"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
