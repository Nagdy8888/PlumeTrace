import { describe, expect, it } from "vitest";

import { gaussianPairs, mulberry32 } from "./random";

describe("random", () => {
  it("mulberry32 is deterministic and stays in [0, 1)", () => {
    const a = mulberry32(7);
    const b = mulberry32(7);
    const first = Array.from({ length: 1000 }, () => a());
    expect(first).toEqual(Array.from({ length: 1000 }, () => b()));
    expect(first.every((v) => v >= 0 && v < 1)).toBe(true);
  });
  it("gaussianPairs returns 2n values with mean near 0 and sd near 1, the same every call", () => {
    const g = gaussianPairs(5000, 7);
    expect(g).toHaveLength(10000);
    expect(Array.from(gaussianPairs(5000, 7))).toEqual(Array.from(g));
    const mean = g.reduce((s, v) => s + v, 0) / g.length;
    const sd = Math.sqrt(g.reduce((s, v) => s + (v - mean) ** 2, 0) / g.length);
    expect(Math.abs(mean)).toBeLessThan(0.05);
    expect(Math.abs(sd - 1)).toBeLessThan(0.05);
  });
});
