"use client";

import { Camera, LogIn, LogOut, MapPin, ScanFace } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { Me } from "@/features/shell/types";
import { cn } from "@/shared/lib/cn";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { formatDuration, timelineSlots } from "../home";
import type { Today } from "../types";

export const ATTENDANCE_HREF = "/app/attendance/today";
const clock = new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit" });
const HOURS = ["08.00", "10.00", "12.00", "14.00", "16.00", "18.00"];

/** P1-E / P1-E2 / D1 "Hari ini": the attendance state and its one next action. */
export function TodayCard({ today, user }: { today: Today; user: Me["user"] }) {
  const now = useNow();
  const session = today.session;
  if (today.state === "not_checked_in" || !session)
    return <NotCheckedIn today={today} user={user} />;

  const start = new Date(session.checked_in_at);
  const end = session.checked_out_at ? new Date(session.checked_out_at) : now;
  const working = today.state === "checked_in";
  const pending = today.pending_reverification;

  return (
    <section
      aria-labelledby="today-duration"
      className="flex flex-col gap-5 rounded-card bg-card p-5 md:p-7"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1.5">
          <p className="font-semibold text-caption text-faint-foreground uppercase tracking-wider lg:hidden">
            Sesi hari ini
          </p>
          <div className="flex flex-wrap items-baseline gap-3">
            <h2 id="today-duration" className="font-display text-title lg:text-display">
              {formatDuration(end.getTime() - start.getTime())}
            </h2>
            <Badge tone={working ? "success" : "neutral"} variant="plain">
              {working ? "Sedang bekerja" : "Hari kerja selesai"}
            </Badge>
          </div>
          <p className="text-body text-muted-foreground">
            Durasi kerja hari ini · check-in {clock.format(start)}
            {session.checked_out_at && ` · check-out ${clock.format(end)}`}
          </p>
        </div>
        {working && (
          <Button asChild className="max-lg:hidden">
            <Link href={ATTENDANCE_HREF}>
              <LogOut />
              Check-out
            </Link>
          </Button>
        )}
      </div>

      <Timeline start={start} end={end} />

      <ul className="flex flex-wrap gap-x-6 gap-y-2 border-border border-t pt-4 text-caption text-muted-foreground max-lg:hidden">
        <li className="flex items-center gap-2">
          <LogIn className="size-4" aria-hidden />
          Check-in {clock.format(start)}
        </li>
        <li className="flex items-center gap-2">
          <Camera className="size-4" aria-hidden />
          Selfie tercatat
        </li>
      </ul>

      {working && (
        <div className="flex flex-col gap-2 lg:hidden">
          <Button asChild size="lg" className={cn(pending && "bg-brand hover:bg-brand/85")}>
            <Link href={ATTENDANCE_HREF}>
              {pending ? <ScanFace /> : <LogOut />}
              {pending ? "Kirim re-verifikasi" : "Check-out"}
            </Link>
          </Button>
          {pending?.due_at && (
            <p className="text-center text-caption text-muted-foreground">
              Diminta sebelum {clock.format(new Date(pending.due_at))} · check-out dari halaman
              Presensi
            </p>
          )}
        </div>
      )}
    </section>
  );
}

function NotCheckedIn({ today, user }: { today: Today; user: Me["user"] }) {
  const place = today.is_remote
    ? "Pekerja lapangan · lokasi bebas"
    : user.work_location
      ? `${user.work_location.name} · radius ${user.work_location.radius_meters} m`
      : "Lokasi kerja belum diatur";
  return (
    <section
      aria-labelledby="today-title"
      className="flex flex-col gap-4 rounded-card bg-card p-5 md:p-7"
    >
      <div className="flex items-center justify-between gap-3">
        <p className="font-semibold text-caption text-faint-foreground uppercase tracking-wider">
          Hari ini
        </p>
        <Badge tone="warning">Belum check-in</Badge>
      </div>
      <h2 id="today-title" className="font-display text-title-sm lg:text-title">
        Siap mulai bekerja?
      </h2>
      <p className="flex items-center gap-2 text-body text-muted-foreground">
        <MapPin className="size-4" aria-hidden />
        {place}
      </p>
      <Button asChild size="lg" className="w-full lg:w-fit">
        <Link href={ATTENDANCE_HREF}>
          <ScanFace />
          Mulai check-in
        </Link>
      </Button>
      <p className="text-caption text-muted-foreground max-lg:text-center">
        3 langkah: prioritas, selfie, lokasi. Sekitar 1 menit.
      </p>
    </section>
  );
}

function Timeline({ start, end }: { start: Date; end: Date }) {
  const slots = timelineSlots(start, end);
  return (
    <figure
      className="flex flex-col gap-2 max-lg:hidden"
      aria-label="Timeline jam kerja 08.00 sampai 18.00"
    >
      <div className="flex h-12 items-end gap-0.5">
        {slots.map((filled, index) => (
          <span
            // biome-ignore lint/suspicious/noArrayIndexKey: slot jam tetap, tidak pernah diurut ulang
            key={index}
            className={cn(
              "flex-1 rounded-[1px]",
              filled ? "h-full bg-foreground" : "h-1.5 bg-secondary",
            )}
          />
        ))}
      </div>
      <div className="flex justify-between text-caption text-faint-foreground">
        {HOURS.map((hour) => (
          <span key={hour}>{hour}</span>
        ))}
      </div>
    </figure>
  );
}

/** Re-renders every minute so the running duration stays current. */
function useNow(): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(id);
  }, []);
  return now;
}
