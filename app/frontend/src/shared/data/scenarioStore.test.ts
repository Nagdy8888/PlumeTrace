import { beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "@/shared/playback";
import { makeReplay } from "@/shared/testing/replayFixture";
import type { ReplayScenario } from "@/shared/types/generated/contract";

import type { DataSource } from "./DataSource";
import { useScenarioStore } from "./scenarioStore";

function deferred<T>(): { promise: Promise<T>; resolve: (v: T) => void } {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

describe("scenarioStore", () => {
  beforeEach(() => {
    useScenarioStore.setState(useScenarioStore.getInitialState());
    useClockStore.setState(useClockStore.getInitialState());
  });

  it("ignores a slow earlier response after a newer selection", async () => {
    const slow = deferred<ReplayScenario>();
    const fast = deferred<ReplayScenario>();
    const source: DataSource = {
      mode: "replay",
      listScenarios: () => Promise.resolve([]),
      loadScenario: (id) => (id === "s1_rod_packing" ? slow.promise : fast.promise),
    };
    const first = useScenarioStore.getState().selectScenario(source, "s1_rod_packing");
    const second = useScenarioStore.getState().selectScenario(source, "s5_sensor_drift");
    fast.resolve(makeReplay({ scenario_id: "s5_sensor_drift", duration_s: 1200, step_s: 60 }));
    await second;
    slow.resolve(makeReplay());
    await first;
    const state = useScenarioStore.getState();
    expect(state.activeId).toBe("s5_sensor_drift");
    expect(state.scenario?.scenario_id).toBe("s5_sensor_drift");
    expect(useClockStore.getState().durationS).toBe(1200);
  });

  it("records a typed error", async () => {
    const { DataSourceError } = await import("./errors");
    const source: DataSource = {
      mode: "live",
      listScenarios: () => Promise.resolve([]),
      loadScenario: () => Promise.reject(new DataSourceError("unreachable", "down")),
    };
    await useScenarioStore.getState().selectScenario(source, "s1_rod_packing");
    expect(useScenarioStore.getState().status).toBe("error");
    expect(useScenarioStore.getState().error?.kind).toBe("unreachable");
  });
});
