import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { waitForAuthTransition } from "@/features/auth/transition";
import { api } from "@/shared/api/client";
import { clearDemoToken } from "@/shared/api/demo-session";

export function useLogout() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [signingOut, setSigningOut] = useState(false);

  const logout = async () => {
    if (signingOut) return;
    const startedAt = Date.now();
    setSigningOut(true);
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      // Local logout must still complete if the server is unavailable.
    } finally {
      await waitForAuthTransition(startedAt);
      clearDemoToken();
      queryClient.clear();
      router.replace("/login");
    }
  };

  return { logout, signingOut };
}
