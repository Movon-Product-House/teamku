export type LeaveStatus = "pending" | "approved" | "rejected" | "revision_requested" | "cancelled";

export type ApprovalRequest = {
  id: string;
  employee_name: string;
  department: string;
  start: string;
  end: string;
  days: number;
  reason: string;
  status: LeaveStatus;
  approver_comment?: string;
  calendar_sync_status?: string;
};

export type ApprovalDecision = "approved" | "rejected" | "revision_requested";

export const leaveStatusLabels: Record<LeaveStatus, string> = {
  pending: "Menunggu",
  approved: "Disetujui",
  rejected: "Ditolak",
  revision_requested: "Perlu revisi",
  cancelled: "Dibatalkan",
};
