"use client";

import { Building2, CircleAlert } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useState } from "react";
import { useLogin } from "@/shared/api/generated";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { AuthTransition } from "@/shared/ui/auth-transition";
import { Button } from "@/shared/ui/button";
import { Field, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";
import { PasswordInput } from "@/shared/ui/password-input";
import { Separator } from "@/shared/ui/separator";
import { loginAlert } from "../auth";
import { useEnterApp } from "../use-enter-app";
import { AuthLayout } from "./auth-layout";
import { DemoAccountPicker, demoCredentials, showDemoAccounts } from "./demo-account-picker";

/** A1: work email + password. Wrong credentials and the lockout are shown inline. */
export function LoginPage() {
  const [email, setEmail] = useState(demoCredentials.email);
  const [password, setPassword] = useState(demoCredentials.password);
  const login = useLogin();
  const { entering, enterApp } = useEnterApp();
  const busy = login.isPending || entering;

  async function submit(event: FormEvent) {
    event.preventDefault();
    const startedAt = Date.now();
    login.mutate(
      { data: { email, password } },
      {
        onSuccess: () => enterApp(startedAt),
      },
    );
  }

  const alert = login.isError ? loginAlert(login.error) : null;
  const edit = (set: (value: string) => void) => (event: React.ChangeEvent<HTMLInputElement>) => {
    set(event.target.value);
    if (login.isError) login.reset();
  };

  return (
    <AuthLayout
      title="Masuk ke Teamku"
      subtitle="Catat kehadiran, ajukan cuti, dan lihat slip gaji dari satu tempat."
    >
      <form className="flex flex-col gap-4.5" onSubmit={submit} noValidate>
        <Field>
          <FieldLabel htmlFor="login-email">Email kerja</FieldLabel>
          <Input
            id="login-email"
            type="email"
            required
            autoComplete="username"
            placeholder="nama@perusahaan.co.id"
            value={email}
            disabled={busy}
            aria-invalid={alert ? true : undefined}
            aria-describedby={alert ? "login-alert" : undefined}
            onChange={edit(setEmail)}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="login-password">Kata sandi</FieldLabel>
          <PasswordInput
            id="login-password"
            required
            autoComplete="current-password"
            value={password}
            disabled={busy}
            aria-invalid={alert ? true : undefined}
            aria-describedby={alert ? "login-alert" : undefined}
            onChange={edit(setPassword)}
          />
        </Field>
        <Link
          href="/forgot-password"
          className="self-end rounded-control font-bold text-caption outline-none hover:underline focus-visible:outline-2 focus-visible:outline-ring"
        >
          Lupa kata sandi?
        </Link>
        <Button
          type="submit"
          size="lg"
          className="mt-2.5 w-full"
          disabled={busy || !email || !password}
        >
          {login.isPending ? "Memeriksa…" : "Masuk"}
        </Button>
      </form>

      {alert && (
        <Alert id="login-alert" variant="destructive" aria-live="polite">
          <CircleAlert aria-hidden />
          <AlertTitle>{alert.title}</AlertTitle>
          <AlertDescription>{alert.body}</AlertDescription>
        </Alert>
      )}

      <div className="flex items-center gap-3">
        <Separator className="flex-1" />
        <span className="font-semibold text-caption text-faint-foreground">Admin HR?</span>
        <Separator className="flex-1" />
      </div>
      <div className="flex flex-col gap-3">
        <Button asChild variant="outline" size="lg" className="w-full">
          <Link href="/signup">
            <Building2 aria-hidden />
            Buat workspace perusahaan
          </Link>
        </Button>
        <p className="text-caption text-faint-foreground">
          Dapat undangan dari HR? Buka tautan di email untuk mengaktifkan akun.
        </p>
      </div>

      {showDemoAccounts && (
        <DemoAccountPicker
          email={email}
          disabled={busy}
          onPick={(credentials) => {
            setEmail(credentials.email);
            setPassword(credentials.password);
            login.reset();
          }}
        />
      )}
      {entering && <AuthTransition message="Menyiapkan workspace…" />}
    </AuthLayout>
  );
}
