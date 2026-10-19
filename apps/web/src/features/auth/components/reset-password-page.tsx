"use client";

import { CircleAlert } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useState } from "react";
import { errorMessage } from "@/shared/api/client";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { Button } from "@/shared/ui/button";
import { useResetPassword, useResetPreview } from "../api";
import { isDeadLink } from "../auth";
import { waitForAuthTransition } from "../transition";
import { AuthChecking, AuthLayout } from "./auth-layout";
import { AuthTransition } from "./auth-transition";
import { DeadLink } from "./dead-link";
import { NewPasswordFields, useNewPassword } from "./new-password-fields";

const NEW_LINK = { href: "/forgot-password", label: "Minta tautan baru" };

/** A3: opened from the reset email. A dead link (unknown, used, > 1 hour) asks for a new one. */
export function ResetPasswordPage() {
  const token = useSearchParams().get("token") ?? "";
  const preview = useResetPreview(token);
  const reset = useResetPassword();
  const fields = useNewPassword();
  const [entering, setEntering] = useState(false);
  const router = useRouter();

  if (!token || (preview.isError && isDeadLink(preview.error)))
    return (
      <DeadLink
        title="Tautan reset tidak berlaku"
        message="Tautan ini sudah tidak berlaku. Minta tautan baru, lalu buka dalam 1 jam."
        action={NEW_LINK}
      />
    );
  if (preview.isPending) return <AuthChecking message="Memeriksa tautan…" />;
  if (preview.isError)
    return (
      <AuthLayout title="Tautan belum bisa diperiksa">
        <Alert variant="destructive">
          <CircleAlert aria-hidden />
          <AlertTitle>Gagal memuat</AlertTitle>
          <AlertDescription>{errorMessage(preview.error, "Coba lagi sebentar.")}</AlertDescription>
        </Alert>
        <Button size="lg" variant="outline" onClick={() => preview.refetch()}>
          Coba lagi
        </Button>
      </AuthLayout>
    );

  function submit(event: FormEvent) {
    event.preventDefault();
    const startedAt = Date.now();
    reset.mutate(
      { token, password: fields.password },
      {
        onSuccess: async () => {
          setEntering(true);
          await waitForAuthTransition(startedAt);
          router.replace("/app/overview");
        },
      },
    );
  }

  if (reset.isError && isDeadLink(reset.error))
    return (
      <DeadLink
        title="Tautan reset tidak berlaku"
        message={errorMessage(reset.error, "Tautan ini sudah tidak berlaku.")}
        action={NEW_LINK}
      />
    );

  const busy = reset.isPending || entering;
  return (
    <AuthLayout logo={false} title="Buat kata sandi baru" subtitle={`Untuk ${preview.data.email}`}>
      <form className="flex flex-col gap-6" onSubmit={submit} noValidate>
        <NewPasswordFields {...fields} disabled={busy} label="Kata sandi baru" />
        {reset.isError && (
          <Alert variant="destructive" aria-live="polite">
            <CircleAlert aria-hidden />
            <AlertTitle>Kata sandi belum tersimpan</AlertTitle>
            <AlertDescription>{errorMessage(reset.error, "Coba lagi sebentar.")}</AlertDescription>
          </Alert>
        )}
        <Button type="submit" size="lg" className="w-full" disabled={busy || !fields.ready}>
          {reset.isPending ? "Menyimpan…" : "Simpan & masuk"}
        </Button>
      </form>
      <p className="text-caption text-faint-foreground">
        Setelah disimpan, sesi Teamku di perangkat lain akan ditutup.
      </p>
      {entering && <AuthTransition message="Menyiapkan workspace…" />}
    </AuthLayout>
  );
}
