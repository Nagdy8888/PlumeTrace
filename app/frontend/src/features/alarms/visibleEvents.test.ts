import { describe, expect, it } from "vitest";

import { makeReplay } from "@/shared/testing/replayFixture";

import { visibleEvents } from "./visibleEvents";

const ev = (sensor_id: string, window_start_s: number) => ({
  sensor_id,
  window_index: window_start_s / 600,
  window_start_s,
  mean_ppm: 8.4,
  baseline_ppm: 2.1,
  downwind_of_site: true,
});

describe("visibleEvents", () => {
  const s = makeReplay({ events: [ev("AT-104", 600), ev("AT-102", 1200), ev("AT-101", 1200)] });
  it("shows an event only once its 10-minute window has closed", () => {
    expect(visibleEvents(s, 1199)).toHaveLength(0);
    expect(visibleEvents(s, 1200)).toHaveLength(1);
    expect(visibleEvents(s, 1800).map((e) => e.sensor_id)).toEqual(["AT-101", "AT-102", "AT-104"]);
  });
  it("handles no scenario", () => {
    expect(visibleEvents(null, 1e9)).toEqual([]);
  });
});
