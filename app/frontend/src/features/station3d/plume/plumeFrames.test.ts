import { describe, expect, it } from "vitest";

import { makeReplay } from "@/shared/testing/replayFixture";

import { decodeKeyframes } from "./plumeFrames";

const grid = (fill: number) => btoa(String.fromCharCode(...new Uint8Array(1200).fill(fill)));

describe("decodeKeyframes", () => {
  it("decodes every frame once", () => {
    const s = makeReplay({
      keyframes: [
        { t_s: 0, wind_speed_m_s: 3, wind_from_deg: 250, stability: "D", sources: [], grid_b64: grid(0) },
        { t_s: 120, wind_speed_m_s: 4, wind_from_deg: 260, stability: "C", sources: [{ anchor_id: "VS-250.tip", rate_kg_h: 15 }], grid_b64: grid(9) },
      ],
    });
    const f = decodeKeyframes(s);
    expect(f.grids).toHaveLength(2);
    expect(f.grids[1]?.[0]).toBe(9);
    expect(f.sources[1]?.[0]?.anchor_id).toBe("VS-250.tip");
    expect(Array.from(f.times)).toEqual([0, 120]);
  });
  it("rejects a grid of the wrong size", () => {
    const s = makeReplay({
      keyframes: [{ t_s: 0, wind_speed_m_s: 3, wind_from_deg: 250, stability: "D", sources: [], grid_b64: btoa("abc") }],
    });
    expect(() => decodeKeyframes(s)).toThrow("plume grid has 3 bytes, expected 1200");
  });
});
