import type { AttendanceState } from "@/features/shell/types";

export type AgendaItem = { title: string | null; status: string | null };

export type Today = {
  state: AttendanceState;
  session: {
    id: string;
    checked_in_at: string;
    checked_out_at: string | null;
    agenda: AgendaItem[];
  } | null;
  pending_reverification: { id: string; due_at: string | null } | null;
  is_remote: boolean;
  closed_hours_today: number;
};

export type Week = {
  target_hours: number;
  days: { date: string; hours: number; late: boolean; on_leave: boolean }[];
};

export type LeaveSummary = {
  items: {
    id: string;
    start: string;
    end: string;
    days: number;
    status: string;
    created_at: string;
  }[];
  balance: { annual_days: number; remaining_days: number };
};

export type Payslip = {
  id: string;
  period: string;
  published_at: string | null;
  net_rupiah: number;
};
