import { CircleAlert, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { errorMessage } from "@/shared/api/client";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { Button } from "@/shared/ui/button";
import { AuthLayout } from "./auth-layout";

/** A3/A4 state: the link is unknown, used, or expired. */
export function DeadLink({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action: { href: string; label: string };
}) {
  return (
    <AuthLayout title={title}>
      <Alert variant="warning">
        <TriangleAlert aria-hidden className="size-4.5" />
        <AlertTitle>Tautan tidak berlaku</AlertTitle>
        <AlertDescription>{message}</AlertDescription>
      </Alert>
      <Button asChild size="lg" className="w-full">
        <Link href={action.href}>{action.label}</Link>
      </Button>
    </AuthLayout>
  );
}

/** A3/A4 state: the token preview failed for a reason other than a dead link (network, 5xx). */
export function PreviewFailed({
  title,
  error,
  onRetry,
}: {
  title: string;
  error: unknown;
  onRetry: () => void;
}) {
  return (
    <AuthLayout title={title}>
      <Alert variant="destructive">
        <CircleAlert aria-hidden />
        <AlertTitle>Gagal memuat</AlertTitle>
        <AlertDescription>{errorMessage(error, "Coba lagi sebentar.")}</AlertDescription>
      </Alert>
      <Button size="lg" variant="outline" onClick={onRetry}>
        Coba lagi
      </Button>
    </AuthLayout>
  );
}
