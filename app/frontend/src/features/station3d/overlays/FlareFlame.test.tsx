import ReactThreeTestRenderer from "@react-three/test-renderer";
import { Object3D, type Mesh, type ShaderMaterial } from "three";
import { beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "@/shared/playback";

import { NodeIndexContext, type NodeIndex } from "../model/nodeIndex";
import { useStationStore } from "../store";
import { FlareFlame } from "./FlareFlame";

function index(withTip: boolean): NodeIndex {
  const tip = new Object3D();
  tip.position.set(185, 30, -30);
  tip.updateMatrixWorld(true);
  return { get: (n) => (withTip && n === "FL-601.tip" ? tip : undefined), equipmentTags: [], missing: [] };
}

async function render(withTip = true): Promise<Awaited<ReturnType<typeof ReactThreeTestRenderer.create>>> {
  return ReactThreeTestRenderer.create(
    <NodeIndexContext.Provider value={index(withTip)}>
      <FlareFlame />
    </NodeIndexContext.Provider>,
  );
}

function material(r: Awaited<ReturnType<typeof render>>): ShaderMaterial {
  return (r.scene.find((n) => n.type === "Mesh").instance as Mesh).material as ShaderMaterial;
}

describe("FlareFlame", () => {
  beforeEach(() => {
    useClockStore.setState(useClockStore.getInitialState());
    useClockStore.getState().reset(600);
    useStationStore.setState({ override: "high", reducedMotion: false });
  });

  it("stands on the flare tip, is not tone mapped and has a bloom gain above 1 on high", async () => {
    const r = await render();
    const flame = r.scene.find((n) => n.props.name === "flare-flame");
    expect(flame.props.position).toEqual([185, 31.2, -30]);
    expect(material(r).toneMapped).toBe(false);
    expect(material(r).uniforms.uGain!.value).toBe(4);
    await r.unmount();
  });

  it("has no bloom gain on the low tier (nothing would pick it up)", async () => {
    useStationStore.setState({ override: "low" });
    const r = await render();
    expect(material(r).uniforms.uGain!.value).toBe(1);
    await r.unmount();
  });

  it("flickers only while the clock plays, at a quarter speed with reduced motion", async () => {
    const r = await render();
    const time = material(r).uniforms.uTime!;
    await r.advanceFrames(2, 0.1);
    expect(time.value).toBe(0);
    useClockStore.getState().play();
    await r.advanceFrames(2, 0.1);
    expect(time.value).toBeCloseTo(0.2, 6);
    useStationStore.setState({ reducedMotion: true });
    await r.advanceFrames(4, 0.1);
    expect(time.value).toBeCloseTo(0.2 + 0.1, 6);
    await r.unmount();
  });

  it("draws nothing when the model has no tip node", async () => {
    const r = await render(false);
    expect(r.scene.findAll((n) => n.props.name === "flare-flame")).toHaveLength(0);
    await r.unmount();
  });
});
