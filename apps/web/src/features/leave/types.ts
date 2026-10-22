import type { LeaveStatus } from "@/shared/api/generated/model";

export const leaveStatusLabels: Record<LeaveStatus, string> = {
  pending: "Menunggu",
  approved: "Disetujui",
  rejected: "Ditolak",
  revision_requested: "Perlu revisi",
  cancelled: "Dibatalkan",
};
