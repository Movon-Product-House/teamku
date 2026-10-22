"use client";

import { CircleAlert, CircleCheck } from "lucide-react";
import { type FormEvent, useState } from "react";
import { errorMessage } from "@/shared/api/client";
import { useChangePassword, useMe } from "@/shared/api/generated";
import { passwordValid } from "@/shared/lib/password";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { Button } from "@/shared/ui/button";
import { Field, FieldDescription, FieldLabel } from "@/shared/ui/field";
import { PasswordInput } from "@/shared/ui/password-input";
import { workLocation } from "../nav";
import { roleLabels } from "../types";

/** P7: work data is read-only (HR owns it); the user can only change their password. */
export function ProfilePage() {
  const me = useMe();
  const change = useChangePassword();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  // The shell only renders its children once /me has loaded.
  if (!me.data) return null;
  const { user } = me.data;

  const rows: [string, string][] = [
    ["Nama", user.name],
    ["Email kerja", user.email],
    ["Departemen", user.department],
    ["Jabatan", user.title],
    ["Role", roleLabels[user.role]],
    ["Lokasi kerja", workLocation(user)],
  ];
  const ready = current !== "" && passwordValid(next);

  function submit(event: FormEvent) {
    event.preventDefault();
    change.mutate(
      { data: { current_password: current, new_password: next } },
      {
        onSuccess: () => {
          setCurrent("");
          setNext("");
        },
      },
    );
  }

  return (
    <div data-surface="v2" className="mx-auto flex w-full max-w-xl flex-col gap-5 pb-5">
      <h1 className="hidden font-display text-title-sm lg:block">Profil & keamanan</h1>

      <section className="flex flex-col gap-2">
        <h2 className="text-faint-foreground text-overline uppercase">Data kerja</h2>
        <dl className="divide-y divide-border rounded-tile border border-border bg-card px-4 py-1">
          {rows.map(([label, value]) => (
            <div key={label} className="flex items-baseline justify-between gap-3 py-3">
              <dt className="text-caption text-faint-foreground">{label}</dt>
              <dd className="text-right font-bold text-caption">{value}</dd>
            </div>
          ))}
        </dl>
        <p className="font-medium text-faint-foreground text-xs">
          Data salah? Minta HR mengubahnya. Kamu tidak bisa mengubah data ini sendiri.
        </p>
      </section>

      <form className="flex flex-col gap-3" onSubmit={submit} noValidate>
        <h2 className="text-faint-foreground text-overline uppercase">Ganti kata sandi</h2>
        {/* Lets password managers update the saved entry for this account. */}
        <input type="hidden" autoComplete="username" value={user.email} readOnly />
        <Field>
          <FieldLabel htmlFor="current-password">Kata sandi saat ini</FieldLabel>
          <PasswordInput
            id="current-password"
            autoComplete="current-password"
            value={current}
            disabled={change.isPending}
            onChange={(event) => {
              change.reset();
              setCurrent(event.target.value);
            }}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="new-password">Kata sandi baru</FieldLabel>
          <PasswordInput
            id="new-password"
            autoComplete="new-password"
            value={next}
            disabled={change.isPending}
            aria-describedby="new-password-hint"
            onChange={(event) => {
              change.reset();
              setNext(event.target.value);
            }}
          />
          <FieldDescription id="new-password-hint">
            8–128 karakter, minimal satu huruf dan satu angka.
          </FieldDescription>
        </Field>
        {change.isError && (
          <Alert variant="destructive" aria-live="polite">
            <CircleAlert aria-hidden />
            <AlertTitle>Kata sandi belum diganti</AlertTitle>
            <AlertDescription>{errorMessage(change.error, "Coba lagi sebentar.")}</AlertDescription>
          </Alert>
        )}
        {change.isSuccess && (
          <Alert aria-live="polite">
            <CircleCheck aria-hidden className="text-success" />
            <AlertTitle>Kata sandi diganti</AlertTitle>
            <AlertDescription>Perangkat lain sudah keluar otomatis.</AlertDescription>
          </Alert>
        )}
        <Button type="submit" size="lg" className="w-full" disabled={!ready || change.isPending}>
          {change.isPending ? "Menyimpan…" : "Simpan kata sandi"}
        </Button>
        <p className="text-center font-medium text-faint-foreground text-xs">
          Perangkat lain akan otomatis keluar setelah kata sandi diganti.
        </p>
      </form>
    </div>
  );
}
