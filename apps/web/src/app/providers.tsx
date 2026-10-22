"use client";

import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { ApiError } from "@/shared/api/client";
import { NotificationHost } from "@/shared/ui/notifications";

function createQueryClient() {
  const queryClient: QueryClient = new QueryClient({
    // Setiap mutation yang sukses menandai semua cache basi: query yang tampil di layar
    // langsung refetch, sisanya saat dibuka lagi. Tidak ada peta "mutation X mengubah
    // query Y" yang bisa lupa diperbarui. Query ber-`meta.keepOnMutation` (pratinjau token)
    // dikecualikan: refetch setelah token dipakai akan mengganti halaman dengan "tautan mati".
    // ponytail: refetch ekstra untuk query aktif; persempit lewat `meta.invalidates` per
    // mutation bila terasa berat.
    mutationCache: new MutationCache({
      // Not returned: MutationCache awaits it, which would hold every mutation pending
      // until all on-screen queries finish refetching.
      onSuccess: () => {
        void queryClient.invalidateQueries({ predicate: (query) => !query.meta?.keepOnMutation });
      },
    }),
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
  return queryClient;
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
