import { useCallback, useEffect, useState } from "react";

/** Seconds left before an action may run again; `start()` restarts the wait. */
export function useCooldown(seconds: number) {
  const [endsAt, setEndsAt] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());

  const running = endsAt !== null && now < endsAt;
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, [running]);

  const start = useCallback(() => {
    setNow(Date.now());
    setEndsAt(Date.now() + seconds * 1000);
  }, [seconds]);

  const left = endsAt === null ? 0 : Math.max(0, (endsAt - now) / 1000);
  return { left, start };
}
