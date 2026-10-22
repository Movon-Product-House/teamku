import { describe, expect, it } from "vitest";
import type { ApprovalOut } from "@/shared/api/generated/model";
import { countApprovals, filterApprovals, validateDecisionComment } from "./approvals";

const request = (id: string, status: ApprovalOut["status"]): ApprovalOut => ({
  id,
  status,
  employee_id: "e1",
  employee_name: "Rina",
  department: "Ops",
  start: "2026-10-01",
  end: "2026-10-02",
  days: 2,
  reason: "Keluarga",
  request_type: "time_off",
  created_at: "2026-09-30T02:00:00Z",
  approver_comment: null,
  calendar_sync_status: "not_applicable",
  employee_calendar_event_id: null,
  team_calendar_event_id: null,
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
