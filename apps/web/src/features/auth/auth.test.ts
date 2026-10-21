import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/api/client";
import {
  companyInitials,
  formatCountdown,
  inviteMeta,
  isDeadLink,
  loginAlert,
  passwordRules,
  passwordValid,
} from "./auth";

describe("password rules", () => {
  it("checks length, a letter and a digit like the API", () => {
    expect(passwordRules("abc").map((rule) => rule.met)).toEqual([false, true, false]);
    expect(passwordValid("Teamku2026")).toBe(true);
    expect(passwordValid("12345678")).toBe(false);
    expect(passwordValid("abcdefgh")).toBe(false);
    expect(passwordValid(`a1${"x".repeat(127)}`)).toBe(false);
    // Emoji are one code point each (2 UTF-16 units): 4 + "a1" = 6 is still too short.
    expect(passwordValid("😀😀😀😀a1")).toBe(false);
    expect(passwordValid("😀😀😀😀😀😀a1")).toBe(true);
  });
});

describe("loginAlert", () => {
  it("tells wrong credentials from the lockout", () => {
    expect(loginAlert(new ApiError("x", 401)).title).toBe("Email atau kata sandi salah");
    expect(loginAlert(new ApiError("x", 422)).title).toBe("Email atau kata sandi salah");
    expect(loginAlert(new ApiError("x", 429)).title).toBe("Akun dikunci sementara");
    expect(loginAlert(new ApiError("Server tidak merespons.", 0)).body).toBe(
      "Server tidak merespons.",
    );
  });
});

describe("isDeadLink", () => {
  it("is true only for unknown or used links", () => {
    expect(isDeadLink(new ApiError("x", 410))).toBe(true);
    expect(isDeadLink(new ApiError("x", 404))).toBe(true);
    expect(isDeadLink(new ApiError("x", 500))).toBe(false);
    expect(isDeadLink(new Error("x"))).toBe(false);
  });
});

describe("inviteMeta", () => {
  const now = new Date("2026-10-19T10:00:00Z");
  it("counts calendar days in Asia/Jakarta", () => {
    expect(inviteMeta("Dewi", "2026-10-25T09:00:00Z", now)).toBe(
      "Diundang oleh Dewi (HR) · berlaku 6 hari lagi",
    );
    expect(inviteMeta(null, "2026-10-19T15:00:00Z", now)).toBe("berlaku sampai hari ini");
    expect(inviteMeta(null, "2026-10-20T10:00:00Z", now)).toBe("berlaku sampai besok");
  });

  it("does not drift around Jakarta midnight", () => {
    // 23:59 WIB on the 19th -> 00:01 WIB on the 20th is tomorrow, not today.
    const late = new Date("2026-10-19T16:59:00Z");
    expect(inviteMeta(null, "2026-10-19T17:01:00Z", late)).toBe("berlaku sampai besok");
    // 00:01 WIB -> 23:59 WIB the same day is still today.
    const early = new Date("2026-10-18T17:01:00Z");
    expect(inviteMeta(null, "2026-10-19T16:59:00Z", early)).toBe("berlaku sampai hari ini");
    // Exactly 7 days later, one minute apart across midnight.
    expect(inviteMeta(null, "2026-10-26T16:59:00Z", late)).toBe("berlaku 7 hari lagi");
  });
});

describe("formatCountdown", () => {
  it("pads seconds and never goes negative", () => {
    expect(formatCountdown(45)).toBe("0:45");
    expect(formatCountdown(65)).toBe("1:05");
    expect(formatCountdown(-3)).toBe("0:00");
  });
});

describe("companyInitials", () => {
  it("uses the first word for multi-word names", () => {
    expect(companyInitials("PT Sinar Nusantara")).toBe("PT");
    expect(companyInitials("movon")).toBe("MO");
  });
});
