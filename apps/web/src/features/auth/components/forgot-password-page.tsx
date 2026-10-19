"use client";

import { CircleAlert, Clock, Inbox, Mail, Send, ShieldCheck } from "lucide-react";
import { type FormEvent, useState } from "react";
import { errorMessage } from "@/shared/api/client";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { Button } from "@/shared/ui/button";
import { Field, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";
import { useForgotPassword } from "../api";
import { formatCountdown } from "../auth";
import { useCooldown } from "../use-cooldown";
import { AuthLayout, BackToLogin } from "./auth-layout";

const RESEND_SECONDS = 45;

/** A2 asks for the work email; A2s always answers the same way (no account enumeration). */
export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sentTo, setSentTo] = useState<string | null>(null);
  const forgot = useForgotPassword();
  const cooldown = useCooldown(RESEND_SECONDS);

  function send(target: string) {
    forgot.mutate(target.trim(), {
      onSuccess: () => {
        setSentTo(target.trim());
        cooldown.start();
      },
    });
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    send(email);
  }

  const failure = forgot.isError && (
    <Alert variant="destructive" aria-live="polite">
      <CircleAlert aria-hidden />
      <AlertTitle>Permintaan belum terkirim</AlertTitle>
      <AlertDescription>{errorMessage(forgot.error, "Coba lagi sebentar.")}</AlertDescription>
    </Alert>
  );

  if (sentTo)
    return (
      <AuthLayout
        logo={false}
        badge={
          <span className="flex size-16 items-center justify-center rounded-card bg-card">
            <Mail aria-hidden className="size-7.5" />
          </span>
        }
        title="Cek email kamu"
        subtitle={`Jika ${sentTo} terdaftar di Teamku, tautan reset sudah kami kirim.`}
      >
        <ul className="flex flex-col gap-2.5 rounded-card bg-card p-4 text-muted-foreground text-sm">
          {[
            { icon: Inbox, text: "Periksa folder Spam atau Promosi" },
            { icon: ShieldCheck, text: "Email dikirim dari noreply@teamku.id" },
            { icon: Clock, text: "Tidak ada email dalam 5 menit? Hubungi HR" },
          ].map(({ icon: Icon, text }) => (
            <li key={text} className="flex items-center gap-2.5">
              <Icon aria-hidden className="size-4 shrink-0 text-faint-foreground" />
              {text}
            </li>
          ))}
        </ul>
        {failure}
        <div className="flex flex-col items-center gap-6">
          <Button
            variant="outline"
            size="lg"
            className="w-full"
            disabled={cooldown.left > 0 || forgot.isPending}
            onClick={() => send(sentTo)}
          >
            {forgot.isPending
              ? "Mengirim…"
              : cooldown.left > 0
                ? `Kirim ulang dalam ${formatCountdown(cooldown.left)}`
                : "Kirim ulang tautan"}
          </Button>
          <BackToLogin icon={false} />
        </div>
      </AuthLayout>
    );

  return (
    <AuthLayout
      logo={false}
      back
      title="Lupa kata sandi?"
      subtitle="Masukkan email kerja. Kami kirim tautan untuk membuat kata sandi baru."
    >
      <form className="flex flex-col gap-6" onSubmit={submit} noValidate>
        <Field>
          <FieldLabel htmlFor="forgot-email">Email kerja</FieldLabel>
          <Input
            id="forgot-email"
            type="email"
            required
            autoComplete="email"
            placeholder="nama@perusahaan.co.id"
            value={email}
            disabled={forgot.isPending}
            onChange={(event) => setEmail(event.target.value)}
          />
        </Field>
        <Button
          type="submit"
          size="lg"
          className="w-full"
          disabled={forgot.isPending || email.trim().length < 5}
        >
          <Send aria-hidden />
          {forgot.isPending ? "Mengirim…" : "Kirim tautan reset"}
        </Button>
      </form>
      {failure}
      <p className="text-caption text-faint-foreground">
        Tautan berlaku 1 jam dan hanya bisa dipakai sekali.
      </p>
    </AuthLayout>
  );
}
