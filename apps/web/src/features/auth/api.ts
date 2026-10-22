import { useQuery } from "@tanstack/react-query";
import { previewReset, usePreviewInvite } from "@/shared/api/generated";

// Token previews never refetch, not even after a mutation (meta.keepOnMutation, see
// providers.tsx): a refetch would swap the page under a half-filled form, and once the
// token is used it would turn into a dead link. The global retry already skips 4xx.
const PREVIEW_OPTIONS = {
  staleTime: Number.POSITIVE_INFINITY,
  refetchOnWindowFocus: false,
  meta: { keepOnMutation: true },
} as const;

// POST keeps the reset token out of the URL, and so out of access logs.
export function useResetPreview(token: string) {
  return useQuery({
    queryKey: ["auth", "reset", token],
    queryFn: () => previewReset({ token }),
    enabled: token !== "",
    ...PREVIEW_OPTIONS,
  });
}

export function useInvitePreview(token: string) {
  // The generated URL builder inserts path params raw; the token comes from ?token=.
  return usePreviewInvite(encodeURIComponent(token), {
    query: { enabled: token !== "", ...PREVIEW_OPTIONS },
  });
}
