import { fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetDataSourceForTests, useScenarioStore } from "@/shared/data";
import { useClockStore } from "@/shared/playback";
import { makeReplay } from "@/shared/testing/replayFixture";

import { ScenarioPicker } from "../components/ScenarioPicker";
import { chooseScenario, retryScenarioLoad, useScenarioBootstrap } from "./useScenarioBootstrap";

const entry = (id: string) => ({ id, title: `Title ${id}`, duration_h: 6, is_mvp: true });

/** Serve the list and the scenarios of the live API from `ids`. */
function serve(ids: string[]): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn((url: string) => {
    if (url === "/api/scenarios") return Promise.resolve(Response.json(ids.map(entry)));
    const id = /\/api\/scenarios\/(.+)\/replay/.exec(url)?.[1] ?? "";
    return Promise.resolve(Response.json(makeReplay({ scenario_id: id, title: `Title ${id}` })));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const active = (): string | null => useScenarioStore.getState().activeId;
const ready = async (): Promise<void> => {
  await waitFor(() => expect(useScenarioStore.getState().status).toBe("ready"));
};

describe("scenario bootstrap", () => {
  beforeEach(() => {
    resetDataSourceForTests();
    useScenarioStore.setState(useScenarioStore.getInitialState());
    useClockStore.setState(useClockStore.getInitialState());
    window.history.replaceState(null, "", "/");
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.replaceState(null, "", "/");
  });

  it("opens S1 by default and reports the live mode", async () => {
    serve(["s1_rod_packing", "s4_planned_blowdown", "s5_sensor_drift"]);
    const { result } = renderHook(() => useScenarioBootstrap());
    await ready();
    expect(active()).toBe("s1_rod_packing");
    await waitFor(() => expect(result.current).toBe("live"));
  });

  it("opens the scenario named by ?scenario= when it is in the list", async () => {
    serve(["s1_rod_packing", "s4_planned_blowdown"]);
    window.history.replaceState(null, "", "/?scenario=s4_planned_blowdown");
    renderHook(() => useScenarioBootstrap());
    await ready();
    expect(active()).toBe("s4_planned_blowdown");
  });

  it("ignores an unknown ?scenario= and opens S1", async () => {
    serve(["s1_rod_packing", "s4_planned_blowdown"]);
    window.history.replaceState(null, "", "/?scenario=s9_nope");
    renderHook(() => useScenarioBootstrap());
    await ready();
    expect(active()).toBe("s1_rod_packing");
  });

  // The data source sorts the list by id, so "first" is the smallest id: s0_warmup sorts before S1.
  it("prefers S1 over the first entry when S1 is in the list but not first", async () => {
    serve(["s0_warmup", "s1_rod_packing"]);
    renderHook(() => useScenarioBootstrap());
    await ready();
    expect(active()).toBe("s1_rod_packing");
  });

  it("an unknown ?scenario= falls back to S1 even when S1 is not first", async () => {
    serve(["s0_warmup", "s1_rod_packing"]);
    window.history.replaceState(null, "", "/?scenario=s9_nope");
    renderHook(() => useScenarioBootstrap());
    await ready();
    expect(active()).toBe("s1_rod_packing");
  });

  it("falls back to the first entry when S1 is not in the list", async () => {
    serve(["s4_planned_blowdown", "s5_sensor_drift"]);
    renderHook(() => useScenarioBootstrap());
    await ready();
    expect(active()).toBe("s4_planned_blowdown");
  });

  it("loads the list once even when the effect runs twice (StrictMode)", async () => {
    const fetchMock = serve(["s1_rod_packing"]);
    const { StrictMode } = await import("react");
    renderHook(() => useScenarioBootstrap(), { wrapper: StrictMode });
    await ready();
    expect(fetchMock.mock.calls.filter(([u]) => u === "/api/scenarios")).toHaveLength(1);
  });

  it("chooseScenario writes ?scenario= and switches", async () => {
    serve(["s1_rod_packing", "s4_planned_blowdown"]);
    await chooseScenario("s4_planned_blowdown");
    expect(window.location.search).toBe("?scenario=s4_planned_blowdown");
    expect(active()).toBe("s4_planned_blowdown");
    expect(useScenarioStore.getState().status).toBe("ready");
  });

  it("retryScenarioLoad reloads the list after a failure, then the scenario after a failed scenario", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("down")));
    renderHook(() => useScenarioBootstrap());
    await waitFor(() => expect(useScenarioStore.getState().indexStatus).toBe("error"));
    serve(["s1_rod_packing"]);
    await retryScenarioLoad();
    expect(useScenarioStore.getState().status).toBe("ready");
    expect(active()).toBe("s1_rod_packing");

    useScenarioStore.setState({ status: "error" });
    const fetchMock = serve(["s1_rod_packing"]);
    await retryScenarioLoad();
    expect(useScenarioStore.getState().status).toBe("ready");
    expect(fetchMock.mock.calls.map(([u]) => u)).toEqual(["/api/scenarios/s1_rod_packing/replay"]);
  });
});

describe("ScenarioPicker", () => {
  beforeEach(() => {
    resetDataSourceForTests();
    useScenarioStore.setState(useScenarioStore.getInitialState());
    useClockStore.setState(useClockStore.getInitialState());
    window.history.replaceState(null, "", "/");
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.replaceState(null, "", "/");
  });

  it("is disabled with a hint while the list is empty", () => {
    render(<ScenarioPicker />);
    const select = screen.getByRole("combobox", { name: "Scenario" });
    expect(select).toBeDisabled();
    expect(select).toHaveDisplayValue("No scenarios loaded");
  });

  it("lists the titles, shows the active one and switches on change", async () => {
    serve(["s1_rod_packing", "s5_sensor_drift"]);
    useScenarioStore.setState({
      index: [entry("s1_rod_packing"), entry("s5_sensor_drift")],
      indexStatus: "ready",
      activeId: "s1_rod_packing",
    });
    render(<ScenarioPicker />);
    const select = screen.getByRole("combobox", { name: "Scenario" });
    expect(screen.getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Title s1_rod_packing",
      "Title s5_sensor_drift",
    ]);
    expect(select).toHaveValue("s1_rod_packing");
    fireEvent.change(select, { target: { value: "s5_sensor_drift" } });
    await waitFor(() => expect(active()).toBe("s5_sensor_drift"));
    expect(window.location.search).toBe("?scenario=s5_sensor_drift");
  });
});
