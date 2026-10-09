import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import type { ApprovalDecision, ApprovalRequest } from "./types";

export const leaveKeys = {
  all: ["leave"] as const,
  approvals: () => [...leaveKeys.all, "approvals"] as const,
};

export function useApprovals() {
  return useQuery({
    queryKey: leaveKeys.approvals(),
    queryFn: () => api<{ items: ApprovalRequest[] }>("/approvals"),
    select: (data) => data.items,
  });
}

export function useDecideApproval() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { id: string; decision: ApprovalDecision; comment: string }) =>
      api<ApprovalRequest>(`/approvals/${input.id}`, {
        method: "POST",
        body: JSON.stringify({ decision: input.decision, comment: input.comment }),
      }),
    // Saldo & daftar cuti karyawan ikut berubah, jadi seluruh cache leave dibuang.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: leaveKeys.all }),
  });
}
