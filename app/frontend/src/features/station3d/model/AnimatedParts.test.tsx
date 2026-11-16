import ReactThreeTestRenderer from "@react-three/test-renderer";
import { Group } from "three";
import { beforeEach, describe, expect, it } from "vitest";

import { useStationStore } from "../store";
import { AnimatedParts } from "./AnimatedParts";
import { buildNodeIndex } from "./nodeIndex";
import { FACILITY } from "./facility";

function rootWithFan(): { root: Group; fan: Group } {
  const root = new Group();
  const cooler = new Group();
  cooler.name = "E-231";
  const fan = new Group();
  fan.name = "E-231__fan_1";
  cooler.add(fan);
  root.add(cooler);
  return { root, fan };
}

describe("AnimatedParts", () => {
  beforeEach(() => useStationStore.setState({ ...useStationStore.getInitialState(), reducedMotion: false }));

  it("spins a fan about its local up axis at 2 rad/s, and at 0.5 rad/s with reduced motion", async () => {
    const { root, fan } = rootWithFan();
    const index = buildNodeIndex(root, FACILITY);
    const r = await ReactThreeTestRenderer.create(<AnimatedParts index={index} />);
    await r.advanceFrames(1, 0.5);
    expect(fan.rotation.y).toBeCloseTo(1.0);
    expect(fan.rotation.x).toBe(0);
    useStationStore.setState({ reducedMotion: true });
    await r.advanceFrames(1, 0.5);
    expect(fan.rotation.y).toBeCloseTo(1.25);
    await r.unmount();
  });

  it("does nothing when the model has no fans", async () => {
    const index = buildNodeIndex(new Group(), FACILITY);
    const r = await ReactThreeTestRenderer.create(<AnimatedParts index={index} />);
    await r.advanceFrames(2, 0.5);
    await r.unmount();
  });
});
