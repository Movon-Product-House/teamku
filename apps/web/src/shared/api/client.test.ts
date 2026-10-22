import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "./client";

function stubFetch(status: number, body: unknown) {
  const fetch = vi.fn(async () => new Response(JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", fetch);
  vi.stubGlobal("window", { setTimeout, clearTimeout, location: { pathname: "/app" } });
  return fetch;
}

afterEach(() => vi.unstubAllGlobals());

describe("api", () => {
  it("sends spec paths through the /api proxy without the API prefix", async () => {
    const fetch = stubFetch(200, { ok: true });
    await expect(api("/api/v1/notifications/read-all", { method: "POST" })).resolves.toEqual({
      ok: true,
    });
    expect(fetch).toHaveBeenCalledWith(
      "/api/notifications/read-all",
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
  });

  it("throws ApiError carrying the status and the ErrorOut body", async () => {
    stubFetch(409, { detail: "Email kerja sudah digunakan" });
    const error = await api("/api/v1/employees").catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      message: "Email kerja sudah digunakan",
      status: 409,
      body: { detail: "Email kerja sudah digunakan" },
    });
  });

  it("falls back to a generic message for field errors", async () => {
    stubFetch(422, {
      detail: [{ loc: ["body", "email"], msg: "Field required", type: "missing" }],
    });
    await expect(api("/api/v1/employees")).rejects.toMatchObject({
      message: "Terjadi kesalahan",
      status: 422,
    });
  });
});
