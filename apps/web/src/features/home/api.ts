import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import type { LeaveSummary, Payslip, Today, Week } from "./types";

// Same keys as the shell and the leave feature, so their invalidations refresh Beranda too.
export const homeKeys = {
  today: ["attendance", "today"] as const,
  week: ["attendance", "week"] as const,
  leave: ["leave", "mine"] as const,
  payslips: ["payroll", "payslips"] as const,
};

export function useToday() {
  return useQuery({ queryKey: homeKeys.today, queryFn: () => api<Today>("/attendance/today") });
}

export function useWeek() {
  return useQuery({ queryKey: homeKeys.week, queryFn: () => api<Week>("/attendance/week") });
}

export function useLeaveSummary() {
  return useQuery({
    queryKey: homeKeys.leave,
    queryFn: () => api<LeaveSummary>("/leave-requests"),
  });
}

export function useLatestPayslip() {
  return useQuery({
    queryKey: homeKeys.payslips,
    queryFn: () => api<{ items: Payslip[] }>("/payroll/payslips"),
    select: (data) => data.items[0] ?? null,
  });
}
