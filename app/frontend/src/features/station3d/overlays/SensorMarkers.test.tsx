import ReactThreeTestRenderer from "@react-three/test-renderer";
import { Color, type InstancedMesh } from "three";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "@/shared/playback";
import { useStationStore } from "../store";
import { useSelectionStore } from "@/shared/selection";
import { makeReplay } from "@/shared/testing/replayFixture";
import type { ReplayScenario } from "@/shared/types/generated/contract";

import { SensorMarkers } from "./SensorMarkers";

const TOKENS = { "--text-2": "#00ff00", "--alarm-med": "#ff0000", "--accent": "#0000ff" };

/** The fixture sensor AT-101 plus three more (4 sensors); AT-102 raises an alarm at 1200 s. */
function scenario(): ReplayScenario {
  const base = makeReplay({
    events: [
      { sensor_id: "AT-102", window_index: 1, window_start_s: 600, mean_ppm: 9, baseline_ppm: 2, downwind_of_site: true },
    ],
  });
  return {
    ...base,
    sensors: [
      ...base.sensors,
      { id: "AT-102", x_m: 60, y_m: 20, z_m: 2 },
      { id: "AT-103", x_m: 120, y_m: 20, z_m: 2 },
      { id: "AT-104", x_m: 180, y_m: 20, z_m: 3 },
    ],
  };
}

type Rendered = Awaited<ReturnType<typeof ReactThreeTestRenderer.create>>;

function mesh(r: Rendered, name: string): InstancedMesh {
  return r.scene.find((n) => n.props.name === name).instance as InstancedMesh;
}

function colourOf(m: InstancedMesh, i: number): string {
  const c = new Color();
  m.getColorAt(i, c);
  return c.getHexString();
}

describe("SensorMarkers", () => {
  beforeEach(() => {
    for (const [name, value] of Object.entries(TOKENS)) document.documentElement.style.setProperty(name, value);
    useSelectionStore.setState(useSelectionStore.getInitialState());
    useClockStore.setState(useClockStore.getInitialState());
    useClockStore.getState().reset(5000);
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  });
  afterEach(() => {
    for (const name of Object.keys(TOKENS)) document.documentElement.style.removeProperty(name);
    document.body.style.cursor = "";
  });

  it("draws one post, one head and one ring instance per sensor (three draw calls) and one hit box each", async () => {
    const r = await ReactThreeTestRenderer.create(<SensorMarkers scenario={scenario()} />);
    expect(mesh(r, "sensor-posts").count).toBe(4);
    expect(mesh(r, "sensor-heads").count).toBe(4);
    expect(mesh(r, "sensor-rings").count).toBe(4);
    expect(r.scene.findAll((n) => n.props.name?.endsWith?.("__hit"))).toHaveLength(4);
    await r.unmount();
  });

  it("keeps the hit boxes invisible so they cost no draw call (the raycaster checks layers, not visible)", async () => {
    const r = await ReactThreeTestRenderer.create(<SensorMarkers scenario={scenario()} />);
    const boxes = r.scene.findAll((n) => n.props.name?.endsWith?.("__hit"));
    expect(boxes.map((b) => b.instance.visible)).toEqual([false, false, false, false]);
    await r.unmount();
  });

  it("selects the sensor tag on a click on its hit box and hovers on pointer over", async () => {
    const r = await ReactThreeTestRenderer.create(<SensorMarkers scenario={scenario()} />);
    const proxy = r.scene.find((n) => n.props.name === "AT-101__hit");
    await r.fireEvent(proxy, "onPointerOver");
    expect(useSelectionStore.getState().hoveredTag).toBe("AT-101");
    expect(document.body.style.cursor).toBe("pointer");
    await r.fireEvent(proxy, "onPointerOut");
    expect(useSelectionStore.getState().hoveredTag).toBeNull();
    await r.fireEvent(proxy, "onClick");
    expect(useSelectionStore.getState().selectedTag).toBe("AT-101");
    await r.unmount();
  });

  it("colours normal, recently alarmed and selected sensors differently, and the alarm fades after 30 minutes", async () => {
    useClockStore.getState().seek(1300);
    const r = await ReactThreeTestRenderer.create(<SensorMarkers scenario={scenario()} />);
    const posts = mesh(r, "sensor-posts");
    const normal = new Color("#00ff00").getHexString();
    expect(colourOf(posts, 0)).toBe(normal);
    expect(colourOf(posts, 1)).toBe(new Color("#ff0000").getHexString());
    await ReactThreeTestRenderer.act(async () => useSelectionStore.getState().select("AT-103"));
    expect(colourOf(mesh(r, "sensor-posts"), 2)).toBe(new Color("#0000ff").getHexString());
    await ReactThreeTestRenderer.act(async () => useClockStore.getState().seek(1200 + 1800 + 60));
    expect(colourOf(mesh(r, "sensor-posts"), 1)).toBe(normal);
    await r.unmount();
  });

  it("shows the ring at full size at once with reduced motion", async () => {
    useStationStore.setState({ reducedMotion: true });
    useClockStore.getState().seek(1300);
    const r = await ReactThreeTestRenderer.create(<SensorMarkers scenario={scenario()} />);
    await r.advanceFrames(1, 0.01);
    expect(mesh(r, "sensor-rings").instanceMatrix.array[1 * 16 + 5]).toBe(1);
    useStationStore.setState({ reducedMotion: false });
    await r.unmount();
  });

  it("scales the ring in only for a recent alarm, in 0.6 s", async () => {
    useClockStore.getState().seek(1300);
    const r = await ReactThreeTestRenderer.create(<SensorMarkers scenario={scenario()} />);
    const rings = mesh(r, "sensor-rings");
    await r.advanceFrames(1, 0.01);
    const scaleY = (i: number): number => rings.instanceMatrix.array[i * 16 + 5] as number;
    expect(scaleY(0)).toBe(0);
    expect(scaleY(1)).toBeGreaterThan(0.59);
    expect(scaleY(1)).toBeLessThan(1);
    await r.advanceFrames(1, 0.7);
    expect(scaleY(1)).toBeCloseTo(1, 6);
    await r.unmount();
  });
});
