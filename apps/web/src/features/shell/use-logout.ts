import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { logout as endSession } from "@/shared/api/generated";
import { waitForAuthTransition } from "@/shared/lib/auth-transition";

export function useLogout() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [signingOut, setSigningOut] = useState(false);

  const logout = async () => {
    if (signingOut) return;
    const startedAt = Date.now();
    setSigningOut(true);
    try {
      // The plain function, not useLogout(): a mutation would invalidate (refetch) /me -> 401.
      await endSession();
    } catch {
      // Local logout must still complete if the server is unavailable.
    } finally {
      await waitForAuthTransition(startedAt);
      await queryClient.cancelQueries();
      // Navigate first; clearing while /app observers are mounted would refetch /me -> 401.
      router.replace("/login");
      queryClient.removeQueries();
    }
  };

  return { logout, signingOut };
}
