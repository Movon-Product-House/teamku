import { describe, expect, it } from "vitest";
import { passwordRules, passwordValid } from "./password";

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
