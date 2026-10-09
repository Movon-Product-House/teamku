"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { ApiError } from "@/shared/api/client";
import { NotificationHost } from "@/shared/ui/notifications";

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        // Error 4xx (izin, validasi, sesi habis) tidak akan berubah bila diulang.
        retry: (failureCount, error) =>
          !(error instanceof ApiError && error.status >= 400 && error.status < 500) &&
          failureCount < 2,
      },
    },
  });
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient);
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <NotificationHost />
    </QueryClientProvider>
  );
}
