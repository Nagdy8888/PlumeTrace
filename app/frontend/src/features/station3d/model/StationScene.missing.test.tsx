import ReactThreeTestRenderer from "@react-three/test-renderer";
import { Group } from "three";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FACILITY } from "./facility";
import { StationScene } from "./StationScene";

/** A root with every tag and anchor except `VS-250.tip` (a list no other test reports). */
function rootMissingOneAnchor(): Group {
  const root = new Group();
  for (const item of FACILITY.equipment) {
    const group = new Group();
    group.name = item.tag;
    for (const anchor of item.anchors ?? []) {
      if (anchor.id === "VS-250.tip") continue;
      const node = new Group();
      node.name = anchor.id;
      group.add(node);
    }
    root.add(group);
  }
  return root;
}

describe("StationScene missing nodes", () => {
  afterEach(() => vi.restoreAllMocks());

  it("logs the missing names once, even after a re-render", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const root = rootMissingOneAnchor();
    const element = <StationScene root={root} spec={FACILITY} labels={false} />;
    const r = await ReactThreeTestRenderer.create(element);
    await r.update(<StationScene root={root} spec={FACILITY} labels={false} />);
    const calls = spy.mock.calls.filter((c) => c[0] === "station model is missing nodes");
    expect(calls).toHaveLength(1);
    expect(calls[0]?.[1]).toEqual(["VS-250.tip"]);
  });
});
