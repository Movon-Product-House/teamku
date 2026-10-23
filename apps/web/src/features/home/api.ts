import { useListApprovals, useListPayslips } from "@/shared/api/generated";
import { pendingLeave } from "./manager-home";

export function useLatestPayslip() {
  return useListPayslips({ query: { select: (data) => data.items[0] ?? null } });
}

export function usePendingLeave(selfId: string) {
  return useListApprovals({ query: { select: (data) => pendingLeave(data.items, selfId) } });
}
