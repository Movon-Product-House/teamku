"use client";

import { create } from "zustand";
import { NotificationDialog, type NotificationDialogState } from "./notification-dialog";

type NotificationStore = {
  current: NotificationDialogState | null;
  notify: (notification: NotificationDialogState) => void;
  close: () => void;
};

// Satu dialog notifikasi global; komponen cukup memanggil notify() tanpa state lokal.
export const useNotificationStore = create<NotificationStore>()((set) => ({
  current: null,
  notify: (notification) => set({ current: notification }),
  close: () => set({ current: null }),
}));

export const notify = (notification: NotificationDialogState) =>
  useNotificationStore.getState().notify(notification);

export function NotificationHost() {
  const current = useNotificationStore((state) => state.current);
  const close = useNotificationStore((state) => state.close);
  return <NotificationDialog notification={current} onClose={close} />;
}
