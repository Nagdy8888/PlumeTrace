import { describe, expect, it } from "vitest";

import { type KeyframePair, keyframeAt, keyframeInto, SIGMA_SLOPE, windTowardInto, windTowardScene } from "./plumeMath";

describe("plumeMath (additions beyond the plan tests)", () => {
  it("clamps the mix to [0, 1] before the first key frame (owner-ratified deviation)", () => {
    expect(keyframeAt(-5, 3)).toEqual({ a: 0, b: 1, mix: 0 });
  });
  it("keyframeInto writes into and returns the same object, and equals keyframeAt", () => {
    for (const [t, count] of [[-5, 3], [130, 180], [1e9, 180], [5, 0]] as const) {
      const out: KeyframePair = { a: 99, b: 99, mix: 99 };
      expect(keyframeInto(t, count, out)).toBe(out);
      expect(out).toEqual(keyframeAt(t, count));
    }
  });
  it("windTowardInto writes into the given pair and agrees with windTowardScene", () => {
    const out: [number, number] = [9, 9];
    expect(windTowardInto(250, out)).toBe(out);
    expect(out).toEqual(windTowardScene(250));
    // wind from 250 deg (WSW) blows toward ENE: +x, and north is -z in the scene
    expect(out[0]).toBeGreaterThan(0.9);
    expect(out[1]).toBeLessThan(0);
  });
  it("has a spread slope for every Pasquill class, widest for A", () => {
    expect(Object.keys(SIGMA_SLOPE)).toEqual(["A", "B", "C", "D", "E", "F"]);
    expect(SIGMA_SLOPE.A[0]).toBeGreaterThan(SIGMA_SLOPE.F[0]);
  });
});
