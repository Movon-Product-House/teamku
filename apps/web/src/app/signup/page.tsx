"use client";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { AuthLink, AuthLinks, AuthShell } from "@/features/auth/components/auth-shell";
import { AuthTransition } from "@/features/auth/components/auth-transition";
import { waitForAuthTransition } from "@/features/auth/transition";
import { api } from "@/shared/api/client";
import { storeDemoToken } from "@/shared/api/demo-session";
import { NotificationDialog, type NotificationDialogState } from "@/shared/ui/notification-dialog";

export default function Signup() {
  const [companyName, setCompanyName] = useState("");
  const [adminName, setAdminName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [notification, setNotification] = useState<NotificationDialogState | null>(null);
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function submit(event: FormEvent) {
    event.preventDefault();
    const startedAt = Date.now();
    setBusy(true);
    try {
      const result = await api<{ access_token: string }>("/auth/signup", {
        method: "POST",
        body: JSON.stringify({
          company_name: companyName,
          admin_name: adminName,
          email,
          password,
        }),
      });
      storeDemoToken(result.access_token);
      await waitForAuthTransition(startedAt);
      router.replace("/app/overview");
    } catch (reason) {
      await waitForAuthTransition(startedAt);
      setNotification({
        type: "error",
        title: "Pendaftaran gagal",
        message: reason instanceof Error ? reason.message : "Pendaftaran gagal",
      });
      setBusy(false);
    }
  }

  return (
    <>
      <AuthShell
        title="Buat workspace perusahaan"
        subtitle="Daftarkan perusahaan Anda dan jadi admin pertamanya."
      >
        <form className="stack" style={{ marginTop: 32 }} onSubmit={submit}>
          <label>
            Nama perusahaan
            <input
              disabled={busy}
              value={companyName}
              onChange={(event) => setCompanyName(event.target.value)}
            />
          </label>
          <label>
            Nama Anda
            <input
              disabled={busy}
              value={adminName}
              onChange={(event) => setAdminName(event.target.value)}
            />
          </label>
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
              autoComplete="new-password"
            />
          </label>
          <button disabled={busy} type="submit">
            {busy ? "Membuat workspace…" : "Buat workspace →"}
          </button>
        </form>
        <AuthLinks>
          Sudah punya akun? <AuthLink href="/login">Masuk</AuthLink>
        </AuthLinks>
      </AuthShell>
      <NotificationDialog notification={notification} onClose={() => setNotification(null)} />
      {busy && <AuthTransition message="Menyiapkan perusahaan Anda…" />}
    </>
  );
}
