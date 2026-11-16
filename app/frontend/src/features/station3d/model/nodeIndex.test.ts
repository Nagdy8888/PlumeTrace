import { Group, Object3D } from "three";
import { describe, expect, it } from "vitest";

import type { FacilitySpec } from "@/shared/types/generated/contract";

import { buildNodeIndex } from "./nodeIndex";

const spec = {
  equipment: [
    { tag: "K-202", anchors: [{ id: "K-202.packing" }, { id: "K-202.engine_exhaust" }] },
    { tag: "VS-250", anchors: [{ id: "VS-250.tip" }] },
  ],
} as unknown as FacilitySpec;

function named<T extends Object3D>(o: T, name: string): T {
  o.name = name;
  return o;
}

describe("buildNodeIndex", () => {
  it("finds tags and anchors and lists what is missing", () => {
    const root = new Group();
    const k = named(new Group(), "K-202");
    k.add(named(new Object3D(), "K-202.packing"));
    root.add(k, named(new Group(), "VS-250"));
    const index = buildNodeIndex(root, spec);
    expect(index.get("K-202")).toBe(k);
    expect(index.get("K-202.packing")?.parent).toBe(k);
    expect(index.equipmentTags).toEqual(["K-202", "VS-250"]);
    expect(index.missing).toEqual(["K-202.engine_exhaust", "VS-250.tip"]);
  });

  it("resolves a loaded anchor by its original name (GLTFLoader strips the dot from node.name)", () => {
    const root = new Group();
    const k = named(new Group(), "K-202");
    const packing = named(new Object3D(), "K-202packing");
    packing.userData.name = "K-202.packing";
    k.add(packing);
    root.add(k, named(new Group(), "VS-250"));
    const index = buildNodeIndex(root, spec);
    expect(index.get("K-202.packing")).toBe(packing);
    expect(index.get("K-202packing")).toBeUndefined();
    expect(index.missing).not.toContain("K-202.packing");
  });

  it("lists only tags present in the scene as equipmentTags and puts absent tags in missing", () => {
    const index = buildNodeIndex(named(new Group(), "root"), spec);
    expect(index.equipmentTags).toEqual([]);
    expect(index.missing).toEqual(["K-202", "K-202.packing", "K-202.engine_exhaust", "VS-250", "VS-250.tip"]);
  });

  it("keeps the first node when a name repeats", () => {
    const root = new Group();
    const first = named(new Group(), "K-202");
    root.add(first, named(new Group(), "K-202"));
    expect(buildNodeIndex(root, spec).get("K-202")).toBe(first);
  });
});
