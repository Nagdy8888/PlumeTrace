import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "@/shared/playback";
import { makeReplay } from "@/shared/testing/replayFixture";

import { useScenarioStore } from "./scenarioStore";
import { useCurrentConditions } from "./useCurrentConditions";

describe("useCurrentConditions", () => {
  beforeEach(() => {
    useScenarioStore.setState(useScenarioStore.getInitialState());
    useClockStore.setState(useClockStore.getInitialState());
  });
  it("is null without a scenario", () => {
    const { result } = renderHook(() => useCurrentConditions());
    expect(result.current).toBeNull();
  });
  it("reads the sample at the clock time", () => {
    const scenario = makeReplay({
      wind_speed_m_s: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
      wind_from_deg: [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
      stability: ["A", "B", "C", "D", "E", "F", "A", "B", "C", "D"],
    });
    useScenarioStore.setState({ scenario, status: "ready" });
    useClockStore.getState().reset(scenario.duration_s);
    useClockStore.getState().seek(185);
    const { result } = renderHook(() => useCurrentConditions());
    expect(result.current).toEqual({ windSpeed_m_s: 4, windFrom_deg: 40, stability: "D" });
  });
});
