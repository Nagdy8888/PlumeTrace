import { beforeEach, describe, expect, it } from "vitest";

import { useStationStore } from "./store";

describe("station store", () => {
  beforeEach(() => useStationStore.setState(useStationStore.getInitialState()));
  it("declines one tier at a time and stops at low", () => {
    const s = useStationStore.getState();
    s.decline();
    expect(useStationStore.getState().autoTier).toBe("medium");
    s.decline();
    s.decline();
    expect(useStationStore.getState().autoTier).toBe("low");
  });
  it("persists a manual override", () => {
    useStationStore.getState().setOverride("low");
    expect(localStorage.getItem("plumetrace.quality")).toBe("low");
  });
});
