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
  });
});

describe("loginAlert", () => {
  it("tells wrong credentials from the lockout", () => {
    expect(loginAlert(new ApiError("x", 401)).title).toBe("Email atau kata sandi salah");
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
  it("rounds the remaining days up", () => {
    expect(inviteMeta("Dewi", "2026-10-25T09:00:00Z", now)).toBe(
      "Diundang oleh Dewi (HR) · berlaku 6 hari lagi",
    );
    expect(inviteMeta(null, "2026-10-19T20:00:00Z", now)).toBe("berlaku sampai hari ini");
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
