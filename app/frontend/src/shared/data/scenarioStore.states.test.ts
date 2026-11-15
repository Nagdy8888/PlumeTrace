import { beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "@/shared/playback";
import { makeReplay } from "@/shared/testing/replayFixture";
import type { ReplayScenario } from "@/shared/types/generated/contract";

import type { DataSource } from "./DataSource";
import { DataSourceError } from "./errors";
import { useScenarioStore } from "./scenarioStore";

const down: DataSource = {
  mode: "live",
  listScenarios: () => Promise.reject(new DataSourceError("unreachable", "down")),
  loadScenario: () => Promise.reject(new DataSourceError("unreachable", "down")),
};

function sourceOf(scenarios: Record<string, ReplayScenario>): DataSource {
  return {
    mode: "replay",
    listScenarios: () => Promise.resolve([]),
    loadScenario: (id) => Promise.resolve(scenarios[id] as ReplayScenario),
  };
}

describe("scenarioStore states", () => {
  beforeEach(() => {
    useScenarioStore.setState(useScenarioStore.getInitialState());
    useClockStore.setState(useClockStore.getInitialState());
  });

  it("backend down: the list ends in an error state with kind unreachable", async () => {
    await useScenarioStore.getState().loadIndex(down);
    const s = useScenarioStore.getState();
    expect(s.indexStatus).toBe("error");
    expect(s.error?.kind).toBe("unreachable");
    expect(s.index).toEqual([]);
  });

  it("loads the list sorted as the source returns it", async () => {
    const entry = { id: "s1_rod_packing", title: "A", duration_h: 6, is_mvp: true };
    const source: DataSource = { ...down, listScenarios: () => Promise.resolve([entry]) };
    await useScenarioStore.getState().loadIndex(source);
    expect(useScenarioStore.getState().index).toEqual([entry]);
    expect(useScenarioStore.getState().indexStatus).toBe("ready");
  });

  it("a switch during playback resets the clock and never mixes old and new data", async () => {
    const a = makeReplay({ duration_s: 600 });
    const b = makeReplay({ scenario_id: "s5_sensor_drift", title: "Other", duration_s: 300 });
    const source = sourceOf({ s1_rod_packing: a, s5_sensor_drift: b });
    await useScenarioStore.getState().selectScenario(source, "s1_rod_packing");
    useClockStore.getState().play();
    useClockStore.getState().tick(0.5);
    expect(useClockStore.getState().tSeconds).toBe(30);

    const pending = useScenarioStore.getState().selectScenario(source, "s5_sensor_drift");
    const during = useScenarioStore.getState();
    expect(during.scenario).toBeNull();
    expect(during.status).toBe("loading");
    expect(useClockStore.getState()).toMatchObject({ tSeconds: 0, durationS: 0, playing: false });

    await pending;
    expect(useScenarioStore.getState().scenario?.title).toBe("Other");
    expect(useClockStore.getState()).toMatchObject({ tSeconds: 0, durationS: 300, playing: false });
  });

  it("aborts the previous request when a new scenario is chosen", async () => {
    const signals: AbortSignal[] = [];
    const source: DataSource = {
      ...down,
      loadScenario: (_id, signal) => {
        if (signal) signals.push(signal);
        return new Promise<ReplayScenario>(() => undefined);
      },
    };
    void useScenarioStore.getState().selectScenario(source, "s1_rod_packing");
    void useScenarioStore.getState().selectScenario(source, "s5_sensor_drift");
    expect(signals[0]?.aborted).toBe(true);
    expect(signals[1]?.aborted).toBe(false);
  });

  it("a late failure of an earlier request does not overwrite the newer scenario", async () => {
    let fail!: (e: unknown) => void;
    const late = new Promise<ReplayScenario>((_, reject) => (fail = reject));
    const source: DataSource = {
      ...down,
      loadScenario: (id) => (id === "s1_rod_packing" ? late : Promise.resolve(makeReplay({ scenario_id: id }))),
    };
    const first = useScenarioStore.getState().selectScenario(source, "s1_rod_packing");
    await useScenarioStore.getState().selectScenario(source, "s5_sensor_drift");
    fail(new DataSourceError("unreachable", "late"));
    await first;
    expect(useScenarioStore.getState().status).toBe("ready");
    expect(useScenarioStore.getState().error).toBeNull();
  });
});
