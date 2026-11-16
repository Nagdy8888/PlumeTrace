import ReactThreeTestRenderer from "@react-three/test-renderer";
import { BoxGeometry, Group, Mesh, type LineBasicMaterial, type LineSegments } from "three";
import { beforeEach, describe, expect, it } from "vitest";

import { useSelectionStore } from "@/shared/selection";

import { FACILITY } from "../model/facility";
import { buildNodeIndex } from "../model/nodeIndex";
import { SelectionBox } from "./SelectionBox";

/** K-202: a 4 x 6 x 2 m box centred at (10, 3, -20). K-201: a bare group (1 m box at x -5). */
function station(): Group {
  const root = new Group();
  const k202 = new Group();
  k202.name = "K-202";
  k202.position.set(10, 0, -20);
  const body = new Mesh(new BoxGeometry(1, 1, 1));
  body.scale.set(4, 6, 2);
  body.position.set(0, 3, 0);
  k202.add(body);
  const k201 = new Group();
  k201.name = "K-201";
  k201.position.set(-5, 0, 5);
  root.add(k202, k201);
  return root;
}

type Renderer = Awaited<ReturnType<typeof ReactThreeTestRenderer.create>>;

/** The two outlines in render order: `[hover, selected]`. */
function outlines(r: Renderer): LineSegments[] {
  return r.scene.findAll((n) => n.type === "LineSegments").map((n) => n.instance as LineSegments);
}

async function setSelection(action: () => void): Promise<void> {
  await ReactThreeTestRenderer.act(async () => action());
}

describe("SelectionBox", () => {
  let r: Renderer;
  beforeEach(async () => {
    useSelectionStore.setState(useSelectionStore.getInitialState());
    r = await ReactThreeTestRenderer.create(<SelectionBox index={buildNodeIndex(station(), FACILITY)} spec={FACILITY} />);
  });

  it("mounts two outlines, both hidden while nothing is selected or hovered", () => {
    const [hover, selected] = outlines(r);
    expect(outlines(r)).toHaveLength(2);
    expect(hover!.visible).toBe(false);
    expect(selected!.visible).toBe(false);
  });

  it("selecting a tag shows the selected outline on that tag's box and keeps the same two objects", async () => {
    const before = outlines(r);
    await setSelection(() => useSelectionStore.getState().select("K-202"));
    const after = outlines(r);
    expect(after).toHaveLength(2);
    expect(after[0]).toBe(before[0]);
    expect(after[1]).toBe(before[1]);
    expect(after[1]!.visible).toBe(true);
    expect(after[1]!.position.toArray()).toEqual([10, 3, -20]);
    expect(after[1]!.scale.toArray()).toEqual([4, 6, 2]);
    expect(after[0]!.visible).toBe(false);
  });

  it("hovering another tag shows the hover outline at half opacity, drawn over the model", async () => {
    await setSelection(() => {
      useSelectionStore.getState().select("K-202");
      useSelectionStore.getState().hover("K-201");
    });
    const [hover, selected] = outlines(r);
    expect(hover!.visible).toBe(true);
    expect(selected!.visible).toBe(true);
    const material = hover!.material as LineBasicMaterial;
    expect(material.opacity).toBe(0.5);
    expect(material.depthTest).toBe(false);
    expect((selected!.material as LineBasicMaterial).opacity).toBe(1);
    expect(hover!.renderOrder).toBe(10);
    expect(selected!.renderOrder).toBe(10);
  });

  it("hides the hover outline when the hovered tag is the selected one", async () => {
    await setSelection(() => {
      useSelectionStore.getState().select("K-202");
      useSelectionStore.getState().hover("K-202");
    });
    const [hover, selected] = outlines(r);
    expect(hover!.visible).toBe(false);
    expect(selected!.visible).toBe(true);
  });

  it("clearing the selection hides the selected outline again without unmounting it", async () => {
    await setSelection(() => useSelectionStore.getState().select("K-202"));
    const mounted = outlines(r)[1];
    await setSelection(() => useSelectionStore.getState().select(null));
    expect(outlines(r)[1]).toBe(mounted);
    expect(mounted!.visible).toBe(false);
  });

  it("outlines an instrument with a 2 m cube", async () => {
    await setSelection(() => useSelectionStore.getState().select("AT-101"));
    const selected = outlines(r)[1]!;
    expect(selected.visible).toBe(true);
    expect(selected.scale.toArray()).toEqual([2, 2, 2]);
  });
});
