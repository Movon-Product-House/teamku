import { describe, expect, it } from "vitest";
import { formatDate, formatMoney, formatPeriod } from "./format";

describe("format", () => {
  it("formats ISO dates as local dates without shifting the day", () => {
    expect(formatDate("2026-01-01")).toBe("01 Jan 2026");
  });

  it("formats a payroll period", () => {
    expect(formatPeriod("2026-10")).toBe("Oktober 2026");
  });

  it("formats rupiah without decimals", () => {
    expect(formatMoney(1500000).replace(/\s/g, " ")).toBe("Rp 1.500.000");
  });
});
