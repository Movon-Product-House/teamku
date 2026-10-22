import { useApprovals, useAttendanceToday, useNotifications } from "@/shared/api/generated";
import type { MeOut } from "@/shared/api/generated/model";

// The shell polls the badge sources once a minute, like the legacy shell did.
const POLL_MS = 60_000;

export function usePolledNotifications() {
  return useNotifications({ query: { refetchInterval: POLL_MS } });
}

export function usePolledAttendanceToday() {
  return useAttendanceToday({ query: { refetchInterval: POLL_MS } });
}

/**
 * Pending approvals for the Persetujuan badge. Same query as the approvals page, so a decision
 * there updates the badge. The approver's own requests are excluded: decide() rejects them with
 * 403. Employees have no approvals, so nothing is fetched for them.
 */
export function usePendingApprovals(me: MeOut | undefined) {
  const userId = me?.user.id;
  return useApprovals({
    query: {
      select: (data) =>
        data.items.filter((item) => item.status === "pending" && item.employee_id !== userId)
          .length,
      enabled: me?.user.role === "manager" || me?.user.role === "hr_admin",
      refetchInterval: POLL_MS,
    },
  });
}
