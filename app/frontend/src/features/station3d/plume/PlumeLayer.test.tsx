import ReactThreeTestRenderer from "@react-three/test-renderer";
import { Object3D, type Mesh, type ShaderMaterial, type DataTexture, type Points } from "three";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useClockStore } from "@/shared/playback";
import { makeReplay } from "@/shared/testing/replayFixture";
import type { ReplayScenario } from "@/shared/types/generated/contract";

import { NodeIndexContext, type NodeIndex } from "../model/nodeIndex";
import { useStationStore } from "../store";
import { PlumeLayer } from "./PlumeLayer";

const grid = (fill: number) => btoa(String.fromCharCode(...new Uint8Array(1200).fill(fill)));

type Frame = ReplayScenario["keyframes"][number];
const frame = (t_s: number, fill: number, anchor: string | null): Frame => ({
  t_s,
  wind_speed_m_s: 3,
  wind_from_deg: 250,
  stability: "D",
  sources: anchor === null ? [] : [{ anchor_id: anchor, rate_kg_h: 15 }],
  grid_b64: grid(fill),
});

/** Three key frames; the source is active from frame 1 (t = 120 s). */
function scenario(anchor = "VS-250.tip"): ReplayScenario {
  return makeReplay({ duration_s: 600, keyframes: [frame(0, 0, null), frame(120, 9, anchor), frame(240, 17, anchor)] });
}

function fakeIndex(): NodeIndex {
  const tip = new Object3D();
  tip.position.set(85, 12, -115);
  tip.updateMatrixWorld(true);
  const nodes = new Map([["VS-250.tip", tip]]);
  return { get: (name) => nodes.get(name), equipmentTags: [], missing: [] };
}

async function render(s: ReplayScenario): Promise<Awaited<ReturnType<typeof ReactThreeTestRenderer.create>>> {
  return ReactThreeTestRenderer.create(
    <NodeIndexContext.Provider value={fakeIndex()}>
      <PlumeLayer scenario={s} />
    </NodeIndexContext.Provider>,
  );
}

function uniform(r: Awaited<ReturnType<typeof render>>, name: string, key: string): unknown {
  const mesh = r.scene.find((n) => n.props.name === name || n.type === name);
  return ((mesh.instance as Mesh).material as ShaderMaterial).uniforms[key]?.value;
}

function points(r: Awaited<ReturnType<typeof render>>): Points[] {
  return r.scene.findAll((n) => n.type === "Points").map((n) => n.instance as Points);
}

describe("PlumeLayer", () => {
  beforeEach(() => {
    useClockStore.setState(useClockStore.getInitialState());
    useStationStore.setState({ override: "high", reducedMotion: false });
    useClockStore.getState().reset(240);
    // the test renderer drives React through act(); without this flag React logs a console.error
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  });
  afterEach(() => vi.restoreAllMocks());

  it("blends the two key frames, loads their grids and advances the particle time only while playing", async () => {
    useClockStore.getState().seek(130);
    useClockStore.getState().play();
    const r = await render(scenario());
    await r.advanceFrames(2, 1 / 60);
    expect(points(r)).toHaveLength(1);
    expect(uniform(r, "plume-heatmap", "uMix") as number).toBeCloseTo(10 / 120, 6);
    const b = uniform(r, "plume-heatmap", "uGridB") as DataTexture;
    expect((b.image.data as Uint8Array)[0]).toBe(17);
    const a = uniform(r, "plume-heatmap", "uGridA") as DataTexture;
    expect((a.image.data as Uint8Array)[0]).toBe(9);
    const time = (points(r)[0]!.material as ShaderMaterial).uniforms.uTime!;
    expect(time.value).toBeCloseTo(2 / 60, 6);
    useClockStore.getState().pause();
    await r.advanceFrames(3, 1 / 60);
    expect(time.value).toBeCloseTo(2 / 60, 6);
    await r.unmount();
  });

  it("draws no particles before the source starts and none for a scenario without key frames", async () => {
    const r = await render(scenario());
    useClockStore.getState().seek(60);
    await r.advanceFrames(1, 1 / 60);
    expect(points(r)).toHaveLength(0);
    await r.unmount();
    const empty = await render(makeReplay());
    await empty.advanceFrames(2, 1 / 60);
    expect(points(empty)).toHaveLength(0);
    await empty.unmount();
  });

  it("after the last key frame the blend stops at 0 and the last grid stays in both textures", async () => {
    const r = await render(makeReplay({ keyframes: [frame(0, 0, null), frame(120, 9, "VS-250.tip")] }));
    useClockStore.getState().seek(130);
    await r.advanceFrames(1, 1 / 60);
    expect(uniform(r, "plume-heatmap", "uMix")).toBe(0);
    expect(((uniform(r, "plume-heatmap", "uGridB") as DataTexture).image.data as Uint8Array)[0]).toBe(9);
    await r.unmount();
  });

  it("splits the tier's particle budget between two sources and gives each its own cloud", async () => {
    const two = makeReplay({
      keyframes: [
        { ...frame(0, 9, "VS-250.tip"), sources: [{ anchor_id: "VS-250.tip", rate_kg_h: 15 }, { anchor_id: "VS-250.tip", rate_kg_h: 5 }] },
      ],
    });
    const r = await render(two);
    await r.advanceFrames(1, 1 / 60);
    const clouds = points(r);
    expect(clouds).toHaveLength(2);
    expect(clouds.every((c) => c.geometry.getAttribute("aOffset").count === 20000)).toBe(true);
    await r.unmount();
  });

  it("hides a source whose anchor is missing and logs one fixed message", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    useClockStore.getState().seek(130);
    const r = await render(scenario("XX-999.tip"));
    await r.advanceFrames(3, 1 / 60);
    expect(points(r)[0]!.visible).toBe(false);
    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith("plume source anchor not found in the station model; source not drawn");
    await r.unmount();
  });

  it("slows the drift to a quarter with reduced motion", async () => {
    useStationStore.setState({ reducedMotion: true });
    useClockStore.getState().seek(130);
    useClockStore.getState().play();
    const r = await render(scenario());
    await r.advanceFrames(4, 1 / 60);
    const time = (points(r)[0]!.material as ShaderMaterial).uniforms.uTime!;
    expect(time.value).toBeCloseTo(0.25 * (4 / 60), 6);
    await r.unmount();
  });
});
