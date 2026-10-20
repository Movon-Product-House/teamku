"use client";

import { LocateFixed } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { errorMessage } from "@/shared/api/client";
import { AuthTransition } from "@/shared/ui/auth-transition";
import { Button } from "@/shared/ui/button";
import { useMe, usePendingApprovals, useTodayAttendance } from "./api";
import { MobileHeader, TabBar } from "./components/mobile-chrome";
import { Sidebar } from "./components/sidebar";
import { navGroups, pageTitle, tabItems } from "./nav";
import { useLogout } from "./use-logout";

const ATTENDANCE_HREF = "/app/attendance/today";

/**
 * App shell v2 (S1 desktop sidebar, S2 mobile top bar + tab bar). `data-surface="v2"` sits on
 * the shell chrome, not on <main>: legacy pages still render inside and rely on legacy CSS.
 * Each v2 screen puts the attribute on its own root.
 */
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const me = useMe();
  const today = useTodayAttendance();
  const pendingApprovals = usePendingApprovals(me.data);
  const { logout, signingOut } = useLogout();

  // Gate on missing data: a failed background refetch keeps the last good `me`.
  if (!me.data)
    return me.isError ? (
      <ShellError
        message={errorMessage(me.error, "Workspace gagal dimuat.")}
        onRetry={() => me.refetch()}
        onLogout={logout}
      />
    ) : (
      <ShellLoading />
    );

  const { user } = me.data;
  const stillWorking = today.data?.state === "checked_in";
  const approvals = pendingApprovals.data ?? 0;

  return (
    <div className="flex min-h-dvh bg-background">
      <Sidebar
        me={me.data}
        groups={navGroups(user.role, user.department)}
        pathname={pathname}
        pendingApprovals={approvals}
        stillWorking={stillWorking}
        onLogout={logout}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <MobileHeader title={pageTitle(pathname, user.role, user.department)} name={user.name} />
        <main className="content w-full flex-1 pb-28 lg:pb-14">
          {today.data?.pending_reverification && !pathname.startsWith(ATTENDANCE_HREF) && (
            <ReverifyBanner />
          )}
          <div className="route-content" key={pathname}>
            {children}
          </div>
        </main>
      </div>
      <TabBar
        items={tabItems(user.role)}
        role={user.role}
        pathname={pathname}
        pendingApprovals={approvals}
      />
      {signingOut && <AuthTransition message="Mengakhiri sesi…" />}
    </div>
  );
}

function ReverifyBanner() {
  return (
    <div
      data-surface="v2"
      role="status"
      className="mb-5 flex items-center gap-3 rounded-field bg-card p-3 pl-3.5"
    >
      <span className="flex size-7 shrink-0 items-center justify-center rounded-control bg-brand text-primary-foreground">
        <LocateFixed aria-hidden className="size-4" />
      </span>
      <p className="flex-1 text-body">Re-verifikasi lokasi diminta. Kirim selfie & lokasi.</p>
      <Button asChild size="sm">
        <Link href={ATTENDANCE_HREF}>Kirim sekarang</Link>
      </Button>
    </div>
  );
}

function ShellLoading() {
  return (
    <div
      data-surface="v2"
      role="status"
      className="flex min-h-dvh items-center justify-center gap-3 bg-background text-body text-muted-foreground"
    >
      <span
        aria-hidden
        className="size-4 animate-spin rounded-full border-2 border-border border-t-foreground"
      />
      Memuat workspace…
    </div>
  );
}

function ShellError({
  message,
  onRetry,
  onLogout,
}: {
  message: string;
  onRetry: () => void;
  onLogout: () => void;
}) {
  return (
    <div
      data-surface="v2"
      className="flex min-h-dvh items-center justify-center bg-background px-5"
    >
      <div role="alert" className="flex max-w-sm flex-col gap-4 rounded-card bg-card p-7">
        <h1 className="font-semibold text-heading">Workspace belum dapat dimuat</h1>
        <p className="text-body text-muted-foreground">{message}</p>
        <div className="flex gap-2">
          <Button onClick={onRetry}>Coba lagi</Button>
          <Button variant="outline" onClick={onLogout}>
            Kembali ke login
          </Button>
        </div>
      </div>
    </div>
  );
}
