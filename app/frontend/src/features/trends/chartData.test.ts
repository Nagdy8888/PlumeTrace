import { describe, expect, it } from "vitest";

import { makeReplay } from "@/shared/testing/replayFixture";

import { highlightedSensors, methaneData, windData } from "./chartData";

describe("chartData", () => {
  const s = makeReplay();
  it("hides values after the current sample", () => {
    const d = methaneData(s, 3);
    expect(d.ids).toEqual(["AT-101"]);
    expect(d.x.slice(0, 3)).toEqual([0, 60, 120]);
    expect(d.series[0]?.[3]).toBeCloseTo(2.3);
    expect(d.series[0]?.[4]).toBeNull();
    expect(windData(s, 0).speed.slice(0, 2)).toEqual([3.5, null]);
  });
  it("highlights the selected methane sensor only", () => {
    expect(highlightedSensors(s, 0, "AT-101")).toEqual(["AT-101"]);
    expect(highlightedSensors(s, 0, "K-202")).toEqual([]);
  });
});
