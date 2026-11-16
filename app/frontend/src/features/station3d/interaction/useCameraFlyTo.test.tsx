import type { CameraControls } from "@react-three/drei";
import ReactThreeTestRenderer from "@react-three/test-renderer";
import type { RefObject } from "react";
import { Group } from "three";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FACILITY } from "../model/facility";
import { StationScene } from "../model/StationScene";
import { REVIEW_CAMERA } from "../scene/reviewCamera";
import { RESET_VIEW_EVENT, useStationStore } from "../store";
import { useSelectionStore } from "@/shared/selection";
import { useCameraFlyTo } from "./useCameraFlyTo";

function fakeRoot(): Group {
  const root = new Group();
  for (const e of FACILITY.equipment) {
    const g = new Group();
    g.name = e.tag;
    const [x, y, z] = e.position_m;
    g.position.set(x, z, -y);
    root.add(g);
  }
  return root;
}

function Harness({ controls }: { controls: RefObject<CameraControls | null> }): null {
  useCameraFlyTo(controls);
  return null;
}

type Renderer = Awaited<ReturnType<typeof ReactThreeTestRenderer.create>>;
const mounted: Renderer[] = [];

async function mount(setLookAt: ReturnType<typeof vi.fn>): Promise<void> {
  const controls = { current: { setLookAt } as unknown as CameraControls };
  const renderer = await ReactThreeTestRenderer.create(
    <StationScene root={fakeRoot()} spec={FACILITY} labels={false}>
      <Harness controls={controls} />
    </StationScene>,
  );
  mounted.push(renderer);
}

describe("useCameraFlyTo", () => {
  const setLookAt = vi.fn();
  beforeEach(() => {
    setLookAt.mockReset();
    useSelectionStore.setState(useSelectionStore.getInitialState());
    useStationStore.setState({ ...useStationStore.getInitialState(), reducedMotion: false });
  });
  afterEach(async () => {
    // Unmount so the window listeners of this test are removed before the next one.
    for (const renderer of mounted.splice(0)) await renderer.unmount();
  });

  it("flies to a selected equipment tag, animated", async () => {
    await mount(setLookAt);
    await ReactThreeTestRenderer.act(async () => useSelectionStore.getState().select("K-202"));
    expect(setLookAt).toHaveBeenCalledTimes(1);
    const args = setLookAt.mock.calls[0]!;
    expect(args).toHaveLength(7);
    expect(args.slice(3, 6)).toEqual([75, 0, -75]); // the 1 m box of a node without geometry, centred on K-202
    expect(args[6]).toBe(true);
  });

  it("jumps instead of flying with reduced motion", async () => {
    useStationStore.setState({ reducedMotion: true });
    await mount(setLookAt);
    await ReactThreeTestRenderer.act(async () => useSelectionStore.getState().select("K-202"));
    expect(setLookAt.mock.calls[0]?.[6]).toBe(false);
  });

  it("flies to an instrument tag and ignores an unknown tag", async () => {
    await mount(setLookAt);
    await ReactThreeTestRenderer.act(async () => useSelectionStore.getState().select("AT-101"));
    expect(setLookAt).toHaveBeenCalledTimes(1);
    await ReactThreeTestRenderer.act(async () => useSelectionStore.getState().select("NOPE-1"));
    expect(setLookAt).toHaveBeenCalledTimes(1);
  });

  it("R and the reset event return to the review camera", async () => {
    await mount(setLookAt);
    window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyR" }));
    window.dispatchEvent(new Event(RESET_VIEW_EVENT));
    expect(setLookAt).toHaveBeenCalledTimes(2);
    expect(setLookAt.mock.calls[0]).toEqual([...REVIEW_CAMERA.position, ...REVIEW_CAMERA.target, true]);
  });

  it("R is ignored with a modifier key and inside a select", async () => {
    await mount(setLookAt);
    window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyR", ctrlKey: true }));
    const select = document.createElement("select");
    document.body.appendChild(select);
    select.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyR", bubbles: true }));
    select.remove();
    expect(setLookAt).not.toHaveBeenCalled();
  });
});
