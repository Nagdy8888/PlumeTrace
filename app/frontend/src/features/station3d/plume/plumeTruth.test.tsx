import { render } from "@testing-library/react";
import ReactThreeTestRenderer from "@react-three/test-renderer";
import { Object3D, type Scene } from "three";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useScenarioStore } from "@/shared/data";
import { useClockStore } from "@/shared/playback";
import { makeReplay } from "@/shared/testing/replayFixture";
import type { ReplayScenario } from "@/shared/types/generated/contract";

import { NodeIndexContext, type NodeIndex } from "../model/nodeIndex";
import { FlareFlame } from "../overlays/FlareFlame";
import { SensorMarkers } from "../overlays/SensorMarkers";
import { WindSock } from "../overlays/WindSock";
import { useStationStore } from "../store";
import { PlumeLayer } from "./PlumeLayer";
import { PlumeLegend } from "./PlumeLegend";

/** A distinctive simulated rate and anchor: none of these may reach any text, name, userData or log. */
const NEEDLES = ["37.25", "37.3", "37.2", "VS-250", "kg/h"] as const;
const grid = (fill: number) => btoa(String.fromCharCode(...new Uint8Array(1200).fill(fill)));

function scenario(anchor = "VS-250.tip"): ReplayScenario {
  const frame = (t_s: number, fill: number, sources: { anchor_id: string; rate_kg_h: number }[]) => ({
    t_s,
    wind_speed_m_s: 3,
    wind_from_deg: 250,
    stability: "D",
    sources,
    grid_b64: grid(fill),
  });
  return makeReplay({
    duration_s: 600,
    keyframes: [frame(0, 0, []), frame(120, 9, [{ anchor_id: anchor, rate_kg_h: 37.25 }])],
  });
}

/** Station nodes the layers look up; they sit outside the scene, so the scene walk never sees them. */
function fakeIndex(): NodeIndex {
  const node = (x: number, y: number, z: number): Object3D => {
    const o = new Object3D();
    o.position.set(x, y, z);
    o.updateMatrixWorld(true);
    return o;
  };
  const nodes = new Map([
    ["VS-250.tip", node(85, 12, -115)],
    ["FL-601.tip", node(185, 30, -30)],
  ]);
  return { get: (name) => nodes.get(name), equipmentTags: [], missing: [] };
}

async function renderLayers(s: ReplayScenario): Promise<Awaited<ReturnType<typeof ReactThreeTestRenderer.create>>> {
  return ReactThreeTestRenderer.create(
    <NodeIndexContext.Provider value={fakeIndex()}>
      <PlumeLayer scenario={s} />
      <SensorMarkers scenario={s} />
      <WindSock scenario={s} />
      <FlareFlame />
    </NodeIndexContext.Provider>,
  );
}

describe("simulation truth in the plume layer (Gate 3 ruling h)", () => {
  beforeEach(() => {
    useScenarioStore.setState(useScenarioStore.getInitialState());
    useClockStore.setState(useClockStore.getInitialState());
    useStationStore.setState({ override: "high", reducedMotion: false });
    useClockStore.getState().reset(600);
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  });
  afterEach(() => vi.restoreAllMocks());

  it("the legend's text and markup hold no source rate, anchor or unit of a rate", () => {
    useScenarioStore.setState({ scenario: scenario(), status: "ready", activeId: "s1_rod_packing" });
    const { container } = render(<PlumeLegend />);
    expect(container.textContent).not.toBe("");
    for (const needle of NEEDLES) {
      expect(container.textContent).not.toContain(needle);
      expect(container.innerHTML).not.toContain(needle);
    }
  });

  it("no scene object has a name or userData that carries the source rate or anchor", async () => {
    useClockStore.getState().seek(130);
    useClockStore.getState().play();
    const r = await renderLayers(scenario());
    await r.advanceFrames(2, 1 / 60);
    const walked: string[] = [];
    (r.scene.instance as Scene).traverse((o) => walked.push(`${o.name} ${JSON.stringify(o.userData)}`));
    expect(walked.some((w) => w.includes("plume-heatmap"))).toBe(true);
    expect(r.scene.findAll((n) => n.type === "Points")).toHaveLength(1);
    for (const needle of NEEDLES) expect(walked.filter((w) => w.includes(needle))).toEqual([]);
    await r.unmount();
  });

  it("an unknown anchor logs one fixed message and no log, warning or error carries the anchor or the rate", async () => {
    const spies = (["error", "warn", "info", "log"] as const).map((m) => vi.spyOn(console, m).mockImplementation(() => undefined));
    useClockStore.getState().seek(130);
    useClockStore.getState().play();
    const r = await renderLayers(scenario("XX-999.tip"));
    await r.advanceFrames(4, 1 / 60);
    await r.unmount();
    const [error] = spies;
    expect(error!).toHaveBeenCalledTimes(1);
    for (const spy of spies) {
      for (const args of spy.mock.calls) {
        for (const arg of args) {
          for (const needle of ["XX-999", "VS-250", "37.25"]) expect(String(arg)).not.toContain(needle);
        }
      }
    }
  });
});
