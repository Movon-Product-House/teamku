import { describe, expect, it } from "vitest";
import { formatDate, formatMoney, formatPeriod, formatShortTime } from "./format";

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

  it("shortens list times to a clock, Kemarin, or a date", () => {
    const now = new Date(2026, 9, 19, 15, 0);
    expect(formatShortTime(new Date(2026, 9, 19, 11, 30).toISOString(), now)).toBe("11.30");
    expect(formatShortTime(new Date(2026, 9, 18, 23, 0).toISOString(), now)).toBe("Kemarin");
    expect(formatShortTime(new Date(2026, 7, 29, 9, 0).toISOString(), now)).toBe("29 Agu");
    expect(formatShortTime(new Date(2025, 11, 31, 9, 0).toISOString(), now)).toBe("31 Des 2025");
  });
});
