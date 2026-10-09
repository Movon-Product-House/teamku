import type { ApprovalDecision, ApprovalRequest, LeaveStatus } from "./types";

export type ApprovalFilter = LeaveStatus | "all";

export const MIN_DECISION_COMMENT = 3;

export function filterApprovals(items: ApprovalRequest[], filter: ApprovalFilter) {
  return filter === "all" ? items : items.filter((item) => item.status === filter);
}

export function countApprovals(items: ApprovalRequest[], filter: ApprovalFilter) {
  return filterApprovals(items, filter).length;
}

export function defaultDecisionComment(decision: ApprovalDecision) {
  return decision === "approved" ? "Disetujui sesuai kebijakan dan saldo cuti." : "";
}

/** Pesan error untuk komentar keputusan, atau null bila valid. */
export function validateDecisionComment(comment: string): string | null {
  return comment.trim().length < MIN_DECISION_COMMENT
    ? `Komentar keputusan minimal ${MIN_DECISION_COMMENT} karakter.`
    : null;
}
