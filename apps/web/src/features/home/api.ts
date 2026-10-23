import { useListPayslips } from "@/shared/api/generated";

export function useLatestPayslip() {
  return useListPayslips({ query: { select: (data) => data.items[0] ?? null } });
}
