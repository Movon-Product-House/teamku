import { describe, expect, it } from "vitest";
import { countApprovals, filterApprovals, validateDecisionComment } from "./approvals";
import type { ApprovalRequest } from "./types";

const request = (id: string, status: ApprovalRequest["status"]): ApprovalRequest => ({
  id,
  status,
  employee_name: "Rina",
  department: "Ops",
  start: "2026-10-01",
  end: "2026-10-02",
  days: 2,
  reason: "Keluarga",
});

describe("approvals", () => {
  const items = [request("1", "pending"), request("2", "approved"), request("3", "pending")];

  it("filters by status and keeps everything for 'all'", () => {
    expect(filterApprovals(items, "pending").map((item) => item.id)).toEqual(["1", "3"]);
    expect(filterApprovals(items, "all")).toHaveLength(3);
    expect(countApprovals(items, "rejected")).toBe(0);
  });

  it("requires a meaningful decision comment", () => {
    expect(validateDecisionComment("  ok ")).toMatch(/minimal 3/);
    expect(validateDecisionComment("Oke")).toBeNull();
  });
});
