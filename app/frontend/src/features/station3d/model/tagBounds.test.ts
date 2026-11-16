import { BoxGeometry, Group, Mesh, Object3D } from "three";
import { describe, expect, it } from "vitest";

import { FACILITY } from "./facility";
import { buildNodeIndex, tagBounds, tagBox } from "./nodeIndex";

/** A tag group at `x` whose only geometry sits in an unnamed child (like the meshopt glb). */
function stationWithTank(): Group {
  const root = new Group();
  const tank = new Group();
  tank.name = "TK-401";
  tank.position.set(10, 0, -20);
  const child = new Mesh(new BoxGeometry(1, 1, 1));
  child.scale.set(4, 6, 2);
  child.position.set(0, 3, 0);
  tank.add(child);
  root.add(tank);
  return root;
}

describe("tagBox and tagBounds", () => {
  it("measures a tag from the meshes of its descendants", () => {
    const tank = stationWithTank().children[0]!;
    const box = tagBox(tank);
    expect(box.min.toArray()).toEqual([8, 0, -21]);
    expect(box.max.toArray()).toEqual([12, 6, -19]);
  });

  it("gives a node without geometry a 1 m box at its world position", () => {
    const empty = new Object3D();
    empty.position.set(3, 4, 5);
    expect(tagBox(empty).getSize(empty.position.clone()).toArray()).toEqual([1, 1, 1]);
    expect(tagBox(empty).getCenter(empty.position.clone()).toArray()).toEqual([3, 4, 5]);
  });

  it("returns the equipment box, a 2 m cube for an instrument, and null for an unknown tag", () => {
    const index = buildNodeIndex(stationWithTank(), FACILITY);
    expect(tagBounds("TK-401", index, FACILITY)).toEqual({ min: [8, 0, -21], max: [12, 6, -19] });
    const at101 = FACILITY.instruments.find((i) => i.tag === "AT-101")!;
    const [x, y, z] = at101.position_m;
    expect(tagBounds("AT-101", index, FACILITY)).toEqual({
      min: [x - 1, z - 1, -y - 1],
      max: [x + 1, z + 1, -y + 1],
    });
    expect(tagBounds("NOPE-1", index, FACILITY)).toBeNull();
  });
});
