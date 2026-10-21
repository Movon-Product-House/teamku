"use client";

import { CircleAlert } from "lucide-react";
import { useSearchParams } from "next/navigation";
import type { FormEvent } from "react";
import { errorMessage } from "@/shared/api/client";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { AuthTransition } from "@/shared/ui/auth-transition";
import { Button } from "@/shared/ui/button";
import { useAcceptInvite, useInvitePreview } from "../api";
import { companyInitials, inviteMeta, isDeadLink } from "../auth";
import type { InvitePreview } from "../types";
import { useEnterApp } from "../use-enter-app";
import { AuthChecking, AuthLayout } from "./auth-layout";
import { DeadLink, PreviewFailed } from "./dead-link";
import { NewPasswordFields, useNewPassword } from "./new-password-fields";

const TO_LOGIN = { href: "/login", label: "Ke halaman masuk" };

/** A4: activate an invite (valid 7 days). Expired and used links get the API's own message. */
export function InvitePage() {
  const token = useSearchParams().get("token") ?? "";
  const preview = useInvitePreview(token);
  const accept = useAcceptInvite();
  const fields = useNewPassword();
  const { entering, enterApp } = useEnterApp();

  const dead = !token
    ? "Tautan undangan tidak lengkap. Buka lagi tautan dari email undangan."
    : preview.isError && isDeadLink(preview.error)
      ? errorMessage(preview.error, "Undangan sudah tidak berlaku.")
      : accept.isError && isDeadLink(accept.error)
        ? errorMessage(accept.error, "Undangan sudah tidak berlaku.")
        : null;
  if (dead) return <DeadLink title="Undangan tidak berlaku" message={dead} action={TO_LOGIN} />;
  if (preview.isPending) return <AuthChecking message="Memeriksa undangan…" />;
  if (preview.isError)
    return (
      <PreviewFailed
        title="Undangan belum bisa diperiksa"
        error={preview.error}
        onRetry={() => preview.refetch()}
      />
    );

  function submit(event: FormEvent) {
    event.preventDefault();
    const startedAt = Date.now();
    accept.mutate(
      { token, password: fields.password },
      {
        onSuccess: () => enterApp(startedAt),
      },
    );
  }

  const invite = preview.data;
  const busy = accept.isPending || entering;
  return (
    <AuthLayout
      badge={<InviteCard invite={invite} />}
      title={`Halo ${invite.name.split(" ")[0]}, aktifkan akunmu`}
      subtitle={`Buat kata sandi untuk ${invite.email}.`}
    >
      <form className="flex flex-col gap-6" onSubmit={submit} noValidate>
        <NewPasswordFields
          {...fields}
          disabled={busy}
          label="Kata sandi baru"
          hint="Simbol boleh, contoh: Teamku2026!"
        />
        {accept.isError && (
          <Alert variant="destructive" aria-live="polite">
            <CircleAlert aria-hidden />
            <AlertTitle>Akun belum aktif</AlertTitle>
            <AlertDescription>{errorMessage(accept.error, "Coba lagi sebentar.")}</AlertDescription>
          </Alert>
        )}
        <Button type="submit" size="lg" className="w-full" disabled={busy || !fields.ready}>
          {accept.isPending ? "Mengaktifkan…" : "Aktifkan akun"}
        </Button>
      </form>
      {entering && <AuthTransition message="Menyiapkan workspace…" />}
    </AuthLayout>
  );
}

function InviteCard({ invite }: { invite: InvitePreview }) {
  return (
    <div className="flex items-center gap-3.5 rounded-card bg-card p-4">
      <span
        aria-hidden
        className="flex size-11 shrink-0 items-center justify-center rounded-field bg-sidebar font-bold text-body text-sidebar-foreground"
      >
        {companyInitials(invite.company)}
      </span>
      <span className="flex min-w-0 flex-col gap-0.5">
        <span className="font-bold text-body">{invite.company}</span>
        <span className="text-caption text-faint-foreground">
          {inviteMeta(invite.invited_by, invite.expires_at)}
        </span>
      </span>
    </div>
  );
}
