import { api } from "./client";

/** Minimal shape the shell needs from an approval row; the leave feature extends it. */
export type ApprovalItem = { id: string; employee_id: string; status: string };

/** Cache key shared by the Persetujuan page and the shell badge, under the `leave` prefix so leave mutations invalidate both. */
export const approvalsKey = ["leave", "approvals"] as const;

export function fetchApprovals<T extends ApprovalItem = ApprovalItem>() {
  return api<{ items: T[] }>("/approvals");
}
