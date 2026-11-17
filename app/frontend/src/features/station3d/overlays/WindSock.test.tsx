import ReactThreeTestRenderer from "@react-three/test-renderer";
import type { Group } from "three";
import { beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "@/shared/playback";
import { makeReplay } from "@/shared/testing/replayFixture";

import { WindSock } from "./WindSock";

type Rendered = Awaited<ReturnType<typeof ReactThreeTestRenderer.create>>;

function groups(r: Rendered): { outer: Group; inner: Group; root: Group } {
  const root = r.scene.find((n) => n.props.name === "windsock").instance as Group;
  const outer = root.children[1] as Group;
  return { root, outer, inner: outer.children[0] as Group };
}

describe("WindSock", () => {
  beforeEach(() => useClockStore.setState(useClockStore.getInitialState()));

  it("stands at MET-01 and points the way the wind blows, level in a strong wind", async () => {
    const s = makeReplay({ wind_from_deg: Array(10).fill(270), wind_speed_m_s: Array(10).fill(8) });
    const r = await ReactThreeTestRenderer.create(<WindSock scenario={s} />);
    const { root, outer, inner } = groups(r);
    expect(root.position.toArray()).toEqual([10, 0, -140]);
    expect(outer.position.y).toBe(10);
    expect(outer.rotation.y).toBeCloseTo(0, 6); // from the west, blowing toward +x
    expect(inner.rotation.z).toBeCloseTo(0, 6);
    await r.unmount();
  });

  it("droops 60 degrees when calm, 30 degrees at 3.5 m/s, and follows the sample index", async () => {
    const speeds = [0, 3.5, ...Array(8).fill(3.5)];
    const s = makeReplay({ wind_from_deg: Array(10).fill(0), wind_speed_m_s: speeds });
    const r = await ReactThreeTestRenderer.create(<WindSock scenario={s} />);
    expect(groups(r).inner.rotation.z).toBeCloseTo(-Math.PI / 3, 6);
    expect(groups(r).outer.rotation.y).toBeCloseTo(-Math.PI / 2, 6); // from the north, blowing toward -z... scene +z
    useClockStore.getState().reset(600);
    await ReactThreeTestRenderer.act(async () => useClockStore.getState().seek(60));
    expect(groups(r).inner.rotation.z).toBeCloseTo(-Math.PI / 6, 6);
    await r.unmount();
  });

  it("draws nothing without a scenario", async () => {
    const r = await ReactThreeTestRenderer.create(<WindSock scenario={null} />);
    expect(r.scene.findAll((n) => n.props.name === "windsock")).toHaveLength(0);
    await r.unmount();
  });
});
