import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { approvalsKey, fetchApprovals } from "@/shared/api/approvals";
import { api } from "@/shared/api/client";
import type { Me, NotificationList, TodayAttendance } from "./types";

// The shell polls the badge sources once a minute, like the legacy shell did.
const POLL_MS = 60_000;

export const shellKeys = {
  me: ["me"] as const,
  notifications: ["notifications"] as const,
  today: ["attendance", "today"] as const,
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

/**
 * Pending approvals for the Persetujuan badge. Shares the cache of the approvals page, so a
 * decision there updates the badge. The approver's own requests are excluded: decide() rejects
 * them with 403. Employees have no approvals, so nothing is fetched for them.
 */
export function usePendingApprovals(me: Me | undefined) {
  const userId = me?.user.id;
  return useQuery({
    queryKey: approvalsKey,
    queryFn: () => fetchApprovals(),
    select: (data) =>
      data.items.filter((item) => item.status === "pending" && item.employee_id !== userId).length,
    enabled: me?.user.role === "manager" || me?.user.role === "hr_admin",
    refetchInterval: POLL_MS,
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (body: { current_password: string; new_password: string }) =>
      api("/auth/change-password", { method: "POST", body: JSON.stringify(body) }),
  });
}

export function useMarkRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api(`/notifications/${id}/read`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: shellKeys.notifications }),
  });
}

export function useMarkAllRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api("/notifications/read-all", { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: shellKeys.notifications }),
  });
}
