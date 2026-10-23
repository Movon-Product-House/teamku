import { useQueryClient } from "@tanstack/react-query";
import { getListApprovalsQueryKey, useDecideApproval } from "@/shared/api/generated";

/**
 * Decide an approval and stay pending until the approvals list has refetched. The global
 * invalidation (providers.tsx) does not wait, so without this the dialog closes while the
 * decided row still shows as pending and can be decided twice.
 */
export function useDecideAndRefresh() {
  const queryClient = useQueryClient();
  return useDecideApproval({
    mutation: {
      onSuccess: () => queryClient.invalidateQueries({ queryKey: getListApprovalsQueryKey() }),
    },
  });
}
