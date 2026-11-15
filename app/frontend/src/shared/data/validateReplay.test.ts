import { describe, expect, it } from "vitest";

import { makeReplay } from "@/shared/testing/replayFixture";

import { DataSourceError } from "./errors";
import { parseReplayIndex, parseReplayScenario } from "./validateReplay";

describe("parseReplayScenario", () => {
  it("accepts a valid file", () => {
    expect(parseReplayScenario(makeReplay(), "s1_rod_packing").scenario_id).toBe("s1_rod_packing");
  });
  it.each([
    ["wrong id", makeReplay({ scenario_id: "s4_planned_blowdown" })],
    ["not simulated", { ...makeReplay(), simulated: false }],
    ["schema version", { ...makeReplay(), schema_version: 2 }],
    ["short series", makeReplay({ series: { "AT-101": [1, 2] } })],
    ["missing unit", makeReplay({ units: {} })],
    ["short wind", makeReplay({ wind_speed_m_s: [1] })],
    ["not an object", "hello"],
  ])("rejects %s", (_label, data) => {
    expect(() => parseReplayScenario(data, "s1_rod_packing")).toThrow(DataSourceError);
  });
});

describe("parseReplayIndex", () => {
  const entries = [
    { id: "s5_sensor_drift", title: "B", duration_h: 6, is_mvp: true },
    { id: "s1_rod_packing", title: "A", duration_h: 6, is_mvp: true },
  ];
  it("accepts the replay index object and sorts by id", () => {
    expect(parseReplayIndex({ schema_version: 1, scenarios: entries }).map((e) => e.id)).toEqual([
      "s1_rod_packing",
      "s5_sensor_drift",
    ]);
  });
  it("accepts the live API array", () => {
    expect(parseReplayIndex(entries)).toHaveLength(2);
  });
  it("rejects malformed entries", () => {
    expect(() => parseReplayIndex([{ id: 3 }])).toThrow(DataSourceError);
  });
});
