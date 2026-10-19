import { Suspense } from "react";
import { ResetPasswordPage } from "@/features/auth/components/reset-password-page";

export default function ResetPassword() {
  return (
    <Suspense>
      <ResetPasswordPage />
    </Suspense>
  );
}
