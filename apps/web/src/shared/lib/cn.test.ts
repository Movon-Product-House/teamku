import { describe, expect, it } from "vitest";
import { cn } from "./cn";

describe("cn", () => {
  it("memperlakukan ukuran teks custom sebagai ukuran, bukan warna", () => {
    expect(cn("text-primary-foreground text-body")).toBe("text-primary-foreground text-body");
    expect(cn("text-success text-caption")).toBe("text-success text-caption");
  });

  it("tetap menggabungkan ukuran teks yang bentrok", () => {
    expect(cn("text-body text-caption")).toBe("text-caption");
  });
});
