"use client";

import { cn } from "cn";
import { CircleAlert, CircleCheck, Info, type LucideIcon } from "lucide-react";
import { Button } from "./button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./dialog";

export type NotificationType = "success" | "error" | "info";

export type NotificationDialogState = {
  type: NotificationType;
  title: string;
  message: string;
};

const appearance: Record<NotificationType, { icon: LucideIcon; eyebrow: string; tone: string }> = {
  success: { icon: CircleCheck, eyebrow: "Berhasil", tone: "bg-success-muted text-success" },
  error: {
    icon: CircleAlert,
    eyebrow: "Perlu perhatian",
    tone: "bg-destructive/10 text-destructive",
  },
  info: { icon: Info, eyebrow: "Notifikasi", tone: "bg-info-muted text-info" },
};

type Props = {
  notification: NotificationDialogState | null;
  onClose: () => void;
};

/** Dialog hasil aksi (berhasil/gagal/info). Fokus, Escape, dan klik overlay ditangani Radix. */
export function NotificationDialog({ notification, onClose }: Props) {
  return (
    <Dialog open={notification !== null} onOpenChange={(open) => !open && onClose()}>
      {notification && <NotificationContent notification={notification} />}
    </Dialog>
  );
}

function NotificationContent({ notification }: { notification: NotificationDialogState }) {
  const { icon: StatusIcon, eyebrow, tone } = appearance[notification.type];
  return (
    <DialogContent showCloseButton={false} className="text-center sm:max-w-sm">
      <DialogHeader className="items-center">
        <span className={cn("mb-1 grid size-11 place-items-center rounded-xl", tone)}>
          <StatusIcon className="size-5" aria-hidden />
        </span>
        <p className="font-semibold text-muted-foreground text-xs uppercase tracking-wider">
          {eyebrow}
        </p>
        <DialogTitle className="font-semibold text-lg leading-snug">
          {notification.title}
        </DialogTitle>
        <DialogDescription>{notification.message}</DialogDescription>
      </DialogHeader>
      <DialogFooter className="sm:justify-center">
        <DialogClose asChild>
          <Button className="w-full sm:w-auto">Mengerti</Button>
        </DialogClose>
      </DialogFooter>
    </DialogContent>
  );
}
