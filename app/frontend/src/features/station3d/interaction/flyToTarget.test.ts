import { describe, expect, it } from "vitest";

import { flyToTarget, instrumentBox } from "./flyToTarget";

describe("flyToTarget", () => {
  it("keeps the camera azimuth and looks down at 30 degrees from at least 12 m", () => {
    const { position, target } = flyToTarget({ min: [0, 0, 0], max: [2, 2, 2] }, [101, 50, 1]);
    expect(target).toEqual([1, 1, 1]);
    const [dx, dy, dz] = [position[0] - 1, position[1] - 1, position[2] - 1];
    expect(Math.hypot(dx, dy, dz)).toBeCloseTo(12);
    expect(Math.atan2(dy, Math.hypot(dx, dz))).toBeCloseTo(Math.PI / 6);
    expect(dz).toBeCloseTo(0);
    expect(dx).toBeGreaterThan(0);
  });
  it("centres a 2 m box on an instrument", () => {
    expect(instrumentBox([195, 75, 2])).toEqual({ min: [194, 1, -76], max: [196, 3, -74] });
  });
});
