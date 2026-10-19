import { TriangleAlert } from "lucide-react";
import Link from "next/link";
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
