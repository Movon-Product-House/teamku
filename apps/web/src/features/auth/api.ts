import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import type { InvitePreview, ResetPreview } from "./types";

export const authKeys = {
  invite: (token: string) => ["auth", "invite", token] as const,
  reset: (token: string) => ["auth", "reset", token] as const,
};

function post<T>(path: string, body: unknown) {
  return api<T>(path, { method: "POST", body: JSON.stringify(body) });
}

// Login, reset and invite acceptance start a session through the httpOnly cookie the API sets.
export function useLogin() {
  return useMutation({
    mutationFn: (input: { email: string; password: string }) => post("/auth/login", input),
  });
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: (email: string) => post<{ ok: boolean }>("/auth/forgot-password", { email }),
  });
}

// Token previews never refetch in the background: a refetch would swap the page under a
// half-filled form. The global retry already skips dead links (4xx).
const PREVIEW_OPTIONS = {
  staleTime: Number.POSITIVE_INFINITY,
  refetchOnWindowFocus: false,
} as const;

// POST keeps the reset token out of the URL, and so out of access logs.
export function useResetPreview(token: string) {
  return useQuery({
    queryKey: authKeys.reset(token),
    queryFn: () => post<ResetPreview>("/auth/reset-password/preview", { token }),
    enabled: token !== "",
    ...PREVIEW_OPTIONS,
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (input: { token: string; password: string }) => post("/auth/reset-password", input),
  });
}

export function useInvitePreview(token: string) {
  return useQuery({
    queryKey: authKeys.invite(token),
    queryFn: () => api<InvitePreview>(`/invites/${encodeURIComponent(token)}`),
    enabled: token !== "",
    ...PREVIEW_OPTIONS,
  });
}

export function useAcceptInvite() {
  return useMutation({
    mutationFn: (input: { token: string; password: string }) => post("/auth/accept-invite", input),
  });
}
