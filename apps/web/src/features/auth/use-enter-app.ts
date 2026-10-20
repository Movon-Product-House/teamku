import { useRouter } from "next/navigation";
import { useState } from "react";
import { waitForAuthTransition } from "./transition";

/** After a successful login/activation/reset: hold the transition screen, then open the app. */
export function useEnterApp() {
  const router = useRouter();
  const [entering, setEntering] = useState(false);

  async function enterApp(startedAt: number) {
    setEntering(true);
    await waitForAuthTransition(startedAt);
    router.replace("/app/overview");
  }

  return { entering, enterApp };
}
