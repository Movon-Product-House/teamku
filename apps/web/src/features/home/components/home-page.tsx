"use client";

import type { UseQueryResult } from "@tanstack/react-query";
import {
  ArrowRight,
  Check,
  ChevronRight,
  History,
  Palmtree,
  Plus,
  ReceiptText,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { type LeaveStatus, leaveStatusLabels } from "@/features/leave/types";
import type { Me } from "@/features/shell/types";
import { errorMessage } from "@/shared/api/client";
import { cn } from "@/shared/lib/cn";
import { formatPeriod } from "@/shared/lib/format";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { useLatestPayslip, useLeaveSummary, useToday, useWeek } from "../api";
import { greeting } from "../home";
import type { AgendaItem, LeaveSummary, Payslip, Today } from "../types";
import { ATTENDANCE_HREF, TodayCard } from "./today-card";
import { WeekCard } from "./week-card";

const LEAVE_HREF = "/app/time/time-off";
const PAYSLIPS_HREF = "/app/payroll/payslips";
const ASK_HREF = "/app/ask-teamku";
const longDate = new Intl.DateTimeFormat("id-ID", {
  weekday: "long",
  day: "numeric",
  month: "long",
});
const compactMoney = new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  notation: "compact",
  maximumFractionDigits: 2,
});
const dayMonth = new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "short" });
const leaveTones = {
  pending: "warning",
  approved: "success",
  rejected: "destructive",
  revision_requested: "warning",
  cancelled: "neutral",
} as const;

/** P1-E, P1-E2 (mobile) and D1 (desktop): Beranda for an Employee. */
export function HomePage({ user }: { user: Me["user"] }) {
  const today = useToday();
  const week = useWeek();
  const leave = useLeaveSummary();
  const payslip = useLatestPayslip();
  const now = new Date();

  return (
    <div data-surface="v2" className="mx-auto flex w-full max-w-6xl flex-col gap-4 pb-5 lg:gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <p className="text-caption text-muted-foreground lg:hidden">{longDate.format(now)}</p>
          <h1 className="font-display text-title-sm lg:text-title">
            {greeting(now)}, {user.name.split(" ")[0]}
          </h1>
          <p className="text-body text-muted-foreground max-lg:hidden">
            {longDate.format(now)} · {user.work_location?.name ?? "Lokasi belum diatur"}
          </p>
        </div>
        <div className="flex gap-2 max-lg:hidden">
          <Button asChild variant="secondary">
            <Link href={ATTENDANCE_HREF}>
              <History />
              Riwayat presensi
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

      <div className="grid gap-4 lg:grid-cols-[1.45fr_1fr] lg:gap-6">
        <Loaded query={today} label="Status presensi" className="min-h-64">
          {(data) => <TodayCard today={data} user={user} />}
        </Loaded>
        <div className="max-lg:hidden">
          <Loaded query={week} label="Jam kerja minggu ini" className="h-full">
            {(data) => <WeekCard week={data} />}
          </Loaded>
        </div>
      </div>

      <h2 className="font-semibold text-heading lg:hidden">Ringkasan saya</h2>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-[1.1fr_1fr_1fr] lg:gap-6">
        <div className="max-lg:hidden">
          <Loaded query={today} label="Agenda hari ini" className="h-full">
            {(data) => <AgendaCard today={data} />}
          </Loaded>
        </div>
        <Loaded query={leave} label="Sisa cuti">
          {(data) => <LeaveCard leave={data} />}
        </Loaded>
        <Loaded query={payslip} label="Slip gaji">
          {(data) => <PayslipCard payslip={data} />}
        </Loaded>
      </div>

      <div className="flex flex-col gap-3 lg:hidden">
        {leave.data?.items[0] && <LatestLeave item={leave.data.items[0]} />}
        <Link
          href={ASK_HREF}
          className="flex items-center gap-3 rounded-card bg-secondary p-4 outline-none focus-visible:outline-2 focus-visible:outline-ring"
        >
          <span className="flex size-10 items-center justify-center rounded-full bg-card">
            <Sparkles className="size-5" aria-hidden />
          </span>
          <span className="flex flex-1 flex-col">
            <span className="font-semibold text-body">Tanya Teamku</span>
            <span className="text-caption text-muted-foreground">Tanya kebijakan perusahaan</span>
          </span>
          <ChevronRight className="size-5" aria-hidden />
        </Link>
      </div>
    </div>
  );
}

/** Loading, error and success for one card; `null` data is each card's own empty state. */
function Loaded<T>({
  query,
  label,
  className,
  children,
}: {
  query: UseQueryResult<T>;
  label: string;
  className?: string;
  children: (data: T) => React.ReactNode;
}) {
  if (query.isPending)
    return (
      <div
        role="status"
        aria-label={`Memuat ${label.toLowerCase()}`}
        className={cn("min-h-32 animate-pulse rounded-card bg-card", className)}
      />
    );
  if (query.isError)
    return (
      <Alert variant="destructive" className={cn("rounded-card p-5", className)}>
        <AlertTitle>{label} belum dapat dimuat</AlertTitle>
        <AlertDescription className="flex flex-col items-start gap-2">
          {errorMessage(query.error, "Coba lagi sebentar lagi.")}
          <Button size="sm" variant="outline" onClick={() => query.refetch()}>
            Coba lagi
          </Button>
        </AlertDescription>
      </Alert>
    );
  return children(query.data);
}

function AgendaCard({ today }: { today: Today }) {
  const items: AgendaItem[] = today.session?.agenda ?? [];
  const done = items.filter((item) => item.status === "done").length;
  return (
    <section
      aria-labelledby="agenda-title"
      className="flex h-full flex-col gap-3 rounded-card bg-card p-7"
    >
      <div className="flex items-start justify-between">
        <h2 id="agenda-title" className="text-heading">
          Agenda hari ini
        </h2>
        {items.length > 0 && (
          <span className="text-caption text-faint-foreground">
            {done} / {items.length}
          </span>
        )}
      </div>
      {items.length === 0 ? (
        <p className="text-body text-muted-foreground">Prioritas hari ini diisi saat check-in.</p>
      ) : (
        // Ticking an item from Beranda waits for the Presensi session issue.
        <ul className="flex flex-col gap-2.5">
          {items.map((item, index) => (
            <li
              // biome-ignore lint/suspicious/noArrayIndexKey: agenda tidak punya id dan tidak diurut ulang
              key={index}
              className={cn(
                "flex items-center gap-3 text-body",
                item.status === "done" && "text-faint-foreground line-through",
              )}
            >
              <span
                aria-hidden
                className={cn(
                  "flex size-5 shrink-0 items-center justify-center rounded-md border border-border",
                  item.status === "done" && "border-primary bg-primary text-primary-foreground",
                )}
              >
                {item.status === "done" && <Check className="size-3.5" />}
              </span>
              <span className="sr-only">{item.status === "done" ? "Selesai: " : "Belum: "}</span>
              {item.title || "Tanpa judul"}
            </li>
          ))}
        </ul>
      )}
      <Link
        href={ATTENDANCE_HREF}
        className="mt-auto flex items-center gap-2 text-caption text-muted-foreground hover:text-foreground"
      >
        <Plus className="size-4" aria-hidden />
        Kelola di Presensi
      </Link>
    </section>
  );
}

function LeaveCard({ leave }: { leave: LeaveSummary }) {
  return (
    <SummaryCard
      icon={Palmtree}
      iconClass="bg-success-muted text-success"
      label="Sisa cuti"
      value={
        <>
          {leave.balance.remaining_days}
          <span className="lg:hidden"> hari</span>
        </>
      }
      note={`dari ${leave.balance.annual_days} hari`}
      href={LEAVE_HREF}
      action="Ajukan cuti"
    />
  );
}

function PayslipCard({ payslip }: { payslip: Payslip | null }) {
  if (!payslip)
    return (
      <SummaryCard
        icon={ReceiptText}
        iconClass="bg-info-muted text-info"
        label="Slip terbaru"
        value="Belum ada"
        quiet
        note="HR belum mempublikasikan slip"
        href={PAYSLIPS_HREF}
        action="Lihat slip"
      />
    );
  const month = formatPeriod(payslip.period).split(" ")[0];
  return (
    <SummaryCard
      icon={ReceiptText}
      iconClass="bg-info-muted text-info"
      label={
        <>
          Slip <span className="lg:hidden">terbaru</span>
          <span className="max-lg:hidden">{month}</span>
        </>
      }
      value={
        <>
          <span className="lg:hidden">{month}</span>
          <span className="max-lg:hidden">{compactMoney.format(payslip.net_rupiah)}</span>
        </>
      }
      note={payslip.published_at ? `Terbit ${dayMonth.format(new Date(payslip.published_at))}` : ""}
      href={PAYSLIPS_HREF}
      action="Lihat slip"
    />
  );
}

function SummaryCard({
  icon: Icon,
  iconClass,
  label,
  value,
  note,
  href,
  action,
  quiet,
}: {
  quiet?: boolean;
  icon: React.ComponentType<{ className?: string }>;
  iconClass: string;
  label: React.ReactNode;
  value: React.ReactNode;
  note: string;
  href: string;
  action: string;
}) {
  return (
    <section className="flex h-full flex-col gap-1 rounded-card bg-card p-4 lg:p-7">
      <span
        aria-hidden
        className={cn(
          "mb-3 flex size-9 items-center justify-center rounded-control lg:hidden",
          iconClass,
        )}
      >
        <Icon className="size-4.5" />
      </span>
      <h2 className="text-caption text-muted-foreground">{label}</h2>
      <p className={cn("font-display text-title-xs", !quiet && "lg:text-display")}>{value}</p>
      <p className="text-caption text-faint-foreground">{note}</p>
      <Link
        href={href}
        className="mt-3 flex items-center gap-1.5 font-semibold text-caption hover:underline max-lg:hidden"
      >
        {action}
        <ArrowRight className="size-3.5" aria-hidden />
      </Link>
    </section>
  );
}

function LatestLeave({ item }: { item: LeaveSummary["items"][number] }) {
  const start = new Date(`${item.start}T00:00:00`);
  const status = item.status as LeaveStatus;
  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-heading">Permohonan cuti</h2>
        <Link href={LEAVE_HREF} className="font-semibold text-caption">
          Lihat semua
        </Link>
      </div>
      <div className="flex items-center gap-3 rounded-card bg-card p-4">
        <span className="flex size-12 shrink-0 flex-col items-center justify-center rounded-control bg-secondary">
          <span className="font-bold text-caption uppercase">
            {start.toLocaleDateString("id-ID", { month: "short" })}
          </span>
          <span className="font-display text-heading">{start.getDate()}</span>
        </span>
        <span className="flex flex-1 flex-col">
          <span className="font-semibold text-body">Cuti · {item.days} hari kerja</span>
          <span className="text-caption text-muted-foreground">
            {dayMonth.format(start)} – {dayMonth.format(new Date(`${item.end}T00:00:00`))}
          </span>
        </span>
        <Badge tone={leaveTones[status] ?? "neutral"}>
          {leaveStatusLabels[status] ?? item.status}
        </Badge>
      </div>
    </section>
  );
}
