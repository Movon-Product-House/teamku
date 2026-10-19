import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import type { Me, NotificationList, Role, TodayAttendance } from "./types";

// The shell polls the badge sources once a minute, like the legacy shell did.
const POLL_MS = 60_000;

export const shellKeys = {
  me: ["me"] as const,
  notifications: ["notifications"] as const,
  today: ["attendance", "today"] as const,
  dashboard: ["dashboard"] as const,
};

export function useMe() {
  return useQuery({ queryKey: shellKeys.me, queryFn: () => api<Me>("/me") });
}

export function useNotifications() {
  return useQuery({
    queryKey: shellKeys.notifications,
    queryFn: () => api<NotificationList>("/notifications"),
    refetchInterval: POLL_MS,
  });
}

export function useTodayAttendance() {
  return useQuery({
    queryKey: shellKeys.today,
    queryFn: () => api<TodayAttendance>("/attendance/today"),
    refetchInterval: POLL_MS,
  });
}

/** Pending approvals for the Persetujuan badge. Employees have none, so it is not fetched. */
export function usePendingApprovals(role: Role | undefined) {
  return useQuery({
    queryKey: shellKeys.dashboard,
    queryFn: () => api<{ pending_approvals: number }>("/dashboard"),
    select: (data) => data.pending_approvals,
    enabled: role === "manager" || role === "hr_admin",
    refetchInterval: POLL_MS,
  });
}

export function useMarkAllRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api("/notifications/read-all", { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: shellKeys.notifications }),
  });
}
