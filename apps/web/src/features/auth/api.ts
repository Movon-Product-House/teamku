import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { storeDemoToken } from "@/shared/api/demo-session";
import type { AuthOut, InvitePreview, ResetPreview } from "./types";

export const authKeys = {
  invite: (token: string) => ["auth", "invite", token] as const,
  reset: (token: string) => ["auth", "reset", token] as const,
};

function post<T>(path: string, body: unknown) {
  return api<T>(path, { method: "POST", body: JSON.stringify(body) });
}

/** The API sets the httpOnly cookie; the demo token copy is kept for `X-Demo-User`. */
function startSession(out: AuthOut) {
  storeDemoToken(out.access_token);
}

export function useLogin() {
  return useMutation({
    mutationFn: (input: { email: string; password: string }) => post<AuthOut>("/auth/login", input),
    onSuccess: startSession,
  });
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: (email: string) => post<{ ok: boolean }>("/auth/forgot-password", { email }),
  });
}

// Dead links (404/410) are final, so token previews never retry.
export function useResetPreview(token: string) {
  return useQuery({
    queryKey: authKeys.reset(token),
    queryFn: () => api<ResetPreview>(`/auth/reset-password/${encodeURIComponent(token)}`),
    enabled: token !== "",
    retry: false,
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (input: { token: string; password: string }) =>
      post<AuthOut>("/auth/reset-password", input),
    onSuccess: startSession,
  });
}

export function useInvitePreview(token: string) {
  return useQuery({
    queryKey: authKeys.invite(token),
    queryFn: () => api<InvitePreview>(`/invites/${encodeURIComponent(token)}`),
    enabled: token !== "",
    retry: false,
  });
}

export function useAcceptInvite() {
  return useMutation({
    mutationFn: (input: { token: string; password: string }) =>
      post<AuthOut>("/auth/accept-invite", input),
    onSuccess: startSession,
  });
}
