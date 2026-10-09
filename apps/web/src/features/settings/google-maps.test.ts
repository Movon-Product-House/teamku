import { describe, expect, it } from "vitest";
import { isGoogleMapsShortUrl, parseGoogleMapsLocation } from "./google-maps";

describe("parseGoogleMapsLocation", () => {
  it("reads raw 'lat, lng' text", () => {
    expect(parseGoogleMapsLocation("-6.2, 106.8166")).toEqual({
      latitude: -6.2,
      longitude: 106.8166,
    });
  });

  it("prefers the place pin over the camera center", () => {
    const url = "https://www.google.com/maps/place/X/@-6.1,106.7,17z/data=!3d-6.2!4d106.8";
    expect(parseGoogleMapsLocation(url)).toEqual({ latitude: -6.2, longitude: 106.8 });
  });

  it("reads the q parameter", () => {
    expect(parseGoogleMapsLocation("https://maps.google.com/?q=-6.25,106.9")).toEqual({
      latitude: -6.25,
      longitude: 106.9,
    });
  });

  it("rejects out-of-range coordinates and empty input", () => {
    expect(parseGoogleMapsLocation("91, 10")).toBeNull();
    expect(parseGoogleMapsLocation("   ")).toBeNull();
  });
});

describe("isGoogleMapsShortUrl", () => {
  it("detects share short links", () => {
    expect(isGoogleMapsShortUrl("https://maps.app.goo.gl/abc")).toBe(true);
    expect(isGoogleMapsShortUrl("https://google.com/maps")).toBe(false);
  });
});
