import { describe, expect, it } from "vitest";
import { newPasswordFits } from "./profile";

describe("newPasswordFits", () => {
  it("accepts 8 to 128 characters", () => {
    expect(newPasswordFits("abcd1234")).toBe(true);
    expect(newPasswordFits(`a1${"x".repeat(126)}`)).toBe(true);
    expect(newPasswordFits("abc1234")).toBe(false);
    expect(newPasswordFits(`a1${"x".repeat(127)}`)).toBe(false);
  });

  it("counts characters like the API does, not UTF-16 units", () => {
    // 4 emoji are 8 UTF-16 units but 4 characters, which the API rejects.
    expect(newPasswordFits("😀😀😀😀")).toBe(false);
    expect(newPasswordFits("😀😀😀😀😀😀😀😀")).toBe(true);
  });
});
