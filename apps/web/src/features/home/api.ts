import { usePayslips } from "@/shared/api/generated";

export function useLatestPayslip() {
  return usePayslips({ query: { select: (data) => data.items[0] ?? null } });
}
