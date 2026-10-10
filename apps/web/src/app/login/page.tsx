"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { AuthLink, AuthLinks, AuthShell } from "@/features/auth/components/auth-shell";
import { AuthTransition } from "@/features/auth/components/auth-transition";
import { DemoAccountPicker, demoCredentials } from "@/features/auth/components/demo-account-picker";
import { waitForAuthTransition } from "@/features/auth/transition";
import { api, errorMessage } from "@/shared/api/client";
import { storeDemoToken } from "@/shared/api/demo-session";
import { notify } from "@/shared/ui/notifications";

export default function Login() {
  const [email, setEmail] = useState(demoCredentials.email);
  const [password, setPassword] = useState(demoCredentials.password);
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function submit(event: FormEvent) {
    event.preventDefault();
    const startedAt = Date.now();
    setBusy(true);
    try {
      const result = await api<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      storeDemoToken(result.access_token);
      await waitForAuthTransition(startedAt);
      router.replace("/app/overview");
    } catch (reason) {
      await waitForAuthTransition(startedAt);
      notify({ type: "error", title: "Login gagal", message: errorMessage(reason, "Login gagal") });
      setBusy(false);
    }
  }

  return (
    <>
      <AuthShell title="Masuk ke workspace Anda" subtitle="Gunakan akun kerja untuk melanjutkan.">
        <form className="stack" style={{ marginTop: 32 }} onSubmit={submit}>
          <label>
            Email kerja
            <input
              disabled={busy}
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
            />
          </label>
          <label>
            Kata sandi
            <input
              disabled={busy}
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>
          <button disabled={busy} type="submit">
            {busy ? "Memverifikasi…" : "Masuk ke Teamku →"}
          </button>
        </form>
        <AuthLinks>
          <AuthLink href="/forgot-password">Lupa kata sandi</AuthLink>
          <span>·</span>
          <AuthLink href="/signup">Buat workspace perusahaan</AuthLink>
        </AuthLinks>
        <DemoAccountPicker
          email={email}
          disabled={busy}
          onPick={(credentials) => {
            setEmail(credentials.email);
            setPassword(credentials.password);
          }}
        />
      </AuthShell>
      {busy && <AuthTransition message="Menyiapkan workspace…" />}
    </>
  );
}
