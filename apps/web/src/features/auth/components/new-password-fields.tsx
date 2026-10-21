"use client";

import { useState } from "react";
import { Field, FieldError, FieldLabel } from "@/shared/ui/field";
import { PasswordInput } from "@/shared/ui/password-input";
import { passwordValid } from "../auth";
import { PasswordRules } from "./password-rules";

export function useNewPassword() {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const mismatch = confirm !== "" && confirm !== password;
  return {
    password,
    confirm,
    setPassword,
    setConfirm,
    mismatch,
    ready: passwordValid(password) && confirm === password,
  };
}

/** New password + live rules + confirmation (A3, A4). */
export function NewPasswordFields({
  password,
  confirm,
  setPassword,
  setConfirm,
  mismatch,
  disabled,
  label,
  hint,
}: ReturnType<typeof useNewPassword> & { disabled: boolean; label: string; hint?: string }) {
  return (
    <>
      <Field>
        <FieldLabel htmlFor="new-password">{label}</FieldLabel>
        <PasswordInput
          id="new-password"
          required
          autoComplete="new-password"
          value={password}
          disabled={disabled}
          aria-describedby="new-password-rules"
          onChange={(event) => setPassword(event.target.value)}
        />
      </Field>
      <PasswordRules id="new-password-rules" password={password} hint={hint} />
      <Field data-invalid={mismatch || undefined}>
        <FieldLabel htmlFor="confirm-password">Ulangi kata sandi</FieldLabel>
        <PasswordInput
          id="confirm-password"
          required
          autoComplete="new-password"
          value={confirm}
          disabled={disabled}
          aria-invalid={mismatch || undefined}
          aria-describedby={mismatch ? "confirm-password-error" : undefined}
          onChange={(event) => setConfirm(event.target.value)}
        />
        {mismatch && <FieldError id="confirm-password-error">Kata sandi belum sama.</FieldError>}
      </Field>
    </>
  );
}
