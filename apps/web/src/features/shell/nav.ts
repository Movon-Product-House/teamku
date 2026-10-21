import {
  BookOpen,
  Calculator,
  CalendarDays,
  History,
  House,
  Inbox,
  LayoutGrid,
  type LucideIcon,
  Plus,
  ReceiptText,
  ScanFace,
  Settings2,
  Sparkles,
  Users,
} from "lucide-react";
import type { Me, Role } from "./types";

export type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
  /** Shows the pending-approvals count next to the label. */
  approvalsBadge?: boolean;
  /** Company modules: usable on a phone, but built for desktop (HM5). */
  desktopOnly?: boolean;
  description?: string;
};

export type NavGroup = { label?: string; items: NavItem[]; shortcuts?: boolean };

export const MORE_HREF = "/app/more";

const home: NavItem = { label: "Beranda", href: "/app/overview", icon: House };
const attendance: NavItem = { label: "Presensi", href: "/app/attendance/today", icon: ScanFace };
const leave: NavItem = { label: "Cuti & Izin", href: "/app/time/time-off", icon: CalendarDays };
const payslips: NavItem = { label: "Slip Gaji", href: "/app/payroll/payslips", icon: ReceiptText };
const ask: NavItem = {
  label: "Ask Teamku",
  href: "/app/ask-teamku",
  icon: Sparkles,
  description: "Tanya kebijakan perusahaan",
};
const approvals: NavItem = {
  label: "Persetujuan",
  href: "/app/approvals",
  icon: Inbox,
  approvalsBadge: true,
};
const people = (label: string): NavItem => ({ label, href: "/app/people", icon: Users });

const personal = [home, attendance, leave, payslips, ask];

// Employees cannot open the HR policy editor, so the policy shortcut goes to Ask Teamku,
// which answers from the published policies. There is no attendance history page yet.
const shortcuts: NavItem[] = [
  { label: "Ajukan cuti", href: leave.href, icon: Plus },
  { label: "Riwayat presensi", href: attendance.href, icon: History },
  { label: "Kebijakan perusahaan", href: ask.href, icon: BookOpen },
];

const company: NavItem[] = [
  { label: "Payroll", href: "/app/payroll/runs", icon: Calculator, desktopOnly: true },
  { label: "Kebijakan", href: "/app/settings/policies", icon: BookOpen, desktopOnly: true },
  {
    label: "Pengaturan",
    href: "/app/settings",
    icon: Settings2,
    desktopOnly: true,
    description: "Lokasi, pengingat, kalender",
  },
];

/** Sidebar groups per role: Saya for everyone, Tim for managers and HR, Perusahaan for HR. */
export function navGroups(role: Role, department: string): NavGroup[] {
  if (role === "manager")
    return [
      { label: "Saya", items: personal },
      { label: `Tim · ${department}`, items: [people("Tim Saya"), approvals] },
    ];
  if (role === "hr_admin")
    return [
      { label: "Saya", items: personal },
      { label: "Tim", items: [people("Karyawan"), approvals] },
      { label: "Perusahaan", items: company },
    ];
  return [{ items: personal }, { label: "Pintasan", items: shortcuts, shortcuts: true }];
}

const more: NavItem = { label: "Lainnya", href: MORE_HREF, icon: LayoutGrid };

/** Mobile tab bar: four items, the last one always Lainnya. */
export function tabItems(role: Role): NavItem[] {
  return role === "employee"
    ? [home, attendance, { ...leave, label: "Cuti" }, more]
    : [home, attendance, approvals, more];
}

/** Groups for the Lainnya screen: every page that is not already a tab. */
export function moreGroups(role: Role, department: string): NavGroup[] {
  const tabs = new Set(tabItems(role).map((item) => item.href));
  return navGroups(role, department)
    .filter((group) => !group.shortcuts)
    .map((group) => ({
      label: group.label ?? "Saya",
      items: group.items.filter((item) => !tabs.has(item.href)),
    }))
    .filter((group) => group.items.length > 0);
}

/** The href that best matches the path: exact or the longest parent, so /app/settings/policies wins over /app/settings. */
export function activeHref(pathname: string, hrefs: string[]): string | undefined {
  return hrefs
    .filter((href) => pathname === href || pathname.startsWith(`${href}/`))
    .sort((a, b) => b.length - a.length)[0];
}

/** The tab to highlight. Pages without a tab of their own live under Lainnya. */
export function activeTab(pathname: string, role: Role): string {
  return (
    activeHref(
      pathname,
      tabItems(role).map((item) => item.href),
    ) ?? MORE_HREF
  );
}

/** Title for the mobile top bar, taken from the nav item that matches the path. */
export function pageTitle(pathname: string, role: Role, department: string): string {
  const items = [more, ...navGroups(role, department).flatMap((group) => group.items)];
  const href = activeHref(
    pathname,
    items.map((item) => item.href),
  );
  return items.find((item) => item.href === href)?.label ?? "Teamku";
}

export function initials(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "--"
  );
}

export function workLocation(user: Pick<Me["user"], "is_remote" | "work_location">): string {
  return user.is_remote ? "Pekerja lapangan" : (user.work_location?.name ?? "Lokasi belum diatur");
}
