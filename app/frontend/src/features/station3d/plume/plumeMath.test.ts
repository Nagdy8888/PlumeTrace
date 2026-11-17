import { describe, expect, it } from "vitest";

import { alphaForPpm, decodeLogU8, keyframeAt, lerpAngleDeg, rateScale, windTowardScene } from "./plumeMath";

describe("plumeMath", () => {
  it("decodes the backend log_u8 encoding", () => {
    expect(decodeLogU8(0)).toBe(0);
    expect(decodeLogU8(1)).toBeCloseTo(0.1, 10);
    expect(decodeLogU8(255)).toBeCloseTo(1000, 6);
    expect(decodeLogU8(128)).toBeCloseTo(0.1 * 10 ** ((127 * 4) / 254), 9);
  });
  it("turns a meteorological 'from' direction into a scene 'toward' vector", () => {
    const [x1, z1] = windTowardScene(270);
    expect(x1).toBeCloseTo(1);
    expect(z1).toBeCloseTo(0);
    const [x2, z2] = windTowardScene(0);
    expect(x2).toBeCloseTo(0);
    expect(z2).toBeCloseTo(1);
  });
  it("interpolates angles along the short arc", () => {
    expect(lerpAngleDeg(350, 10, 0.5)).toBeCloseTo(0);
    expect(lerpAngleDeg(10, 350, 0.25)).toBeCloseTo(5);
  });
  it("finds the two key frames around a time", () => {
    expect(keyframeAt(130, 180)).toEqual({ a: 1, b: 2, mix: 10 / 120 });
    expect(keyframeAt(1e9, 180)).toEqual({ a: 179, b: 179, mix: 0 });
    expect(keyframeAt(5, 0)).toEqual({ a: 0, b: 0, mix: 0 });
  });
  it("maps concentration and rate to visibility", () => {
    expect(alphaForPpm(0.9)).toBe(0);
    expect(alphaForPpm(1)).toBeCloseTo(0.25);
    expect(alphaForPpm(100)).toBeCloseTo(0.75);
    expect(rateScale(1)).toBe(0.3);
    expect(rateScale(30)).toBe(1);
  });
});
