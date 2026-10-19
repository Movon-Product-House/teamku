import { Suspense } from "react";
import { InvitePage } from "@/features/auth/components/invite-page";

export default function Invite() {
  return (
    <Suspense>
      <InvitePage />
    </Suspense>
  );
}
