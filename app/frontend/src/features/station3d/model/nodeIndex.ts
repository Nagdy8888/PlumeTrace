import { createContext, useContext } from "react";
import { Box3, Vector3, type Object3D } from "three";

import type { FacilitySpec } from "@/shared/types/generated/contract";

import { instrumentBox, type Vec3 } from "../interaction/flyToTarget";

/** Lookup from contract names (tags, anchor ids, `<tag>__<part>`) to scene objects. */
export interface NodeIndex {
  get(name: string): Object3D | undefined;
  /** Spec equipment tags that exist in the scene, in spec order. */
  readonly equipmentTags: readonly string[];
  /** Spec tags and anchor ids that the scene does not contain. */
  readonly missing: readonly string[];
}

/**
 * The name a node had in the glb. `GLTFLoader` strips `[ ] . : /` from `node.name` (the anchor
 * `K-202.packing` becomes `K-202packing`) and keeps the original in `userData.name`.
 */
function contractName(node: Object3D): string {
  const original: unknown = node.userData.name;
  return typeof original === "string" ? original : node.name;
}

/**
 * Index the station tree. Every equipment tag and anchor id of the spec must be present;
 * absent names are listed in `missing` (the view logs them once with console.error).
 *
 * @param root - Loaded or procedurally built station root.
 * @param spec - Facility spec (from `shared/facility/ks07.json`).
 * @returns The index.
 */
export function buildNodeIndex(root: Object3D, spec: FacilitySpec): NodeIndex {
  const byName = new Map<string, Object3D>();
  root.traverse((node) => {
    const name = contractName(node);
    if (name !== "" && !byName.has(name)) byName.set(name, node);
  });
  const equipmentTags: string[] = [];
  const missing: string[] = [];
  for (const item of spec.equipment) {
    (byName.has(item.tag) ? equipmentTags : missing).push(item.tag);
    for (const anchor of item.anchors ?? []) if (!byName.has(anchor.id)) missing.push(anchor.id);
  }
  return { get: (name) => byName.get(name), equipmentTags, missing };
}

const ONE_M = new Vector3(1, 1, 1);
const centre = new Vector3();

/**
 * World-space box of a tag node and all its descendants (the meshes sit in child nodes of the
 * glb). A node without geometry gets a 1 m box at its world position.
 *
 * @param node - Equipment node from the index.
 * @returns A new box in scene coordinates.
 */
export function tagBox(node: Object3D): Box3 {
  node.updateWorldMatrix(true, true);
  const box = new Box3().setFromObject(node);
  if (box.isEmpty()) box.setFromCenterAndSize(node.getWorldPosition(centre), ONE_M);
  return box;
}

/**
 * Box to frame or outline for a selected tag: the equipment node's world box, or a 2 m cube
 * around an instrument.
 *
 * @param tag - Equipment tag or instrument tag.
 * @param index - Node index of the station.
 * @param spec - Facility spec (instrument positions).
 * @returns The box in scene coordinates, or null for an unknown tag.
 */
export function tagBounds(
  tag: string,
  index: NodeIndex,
  spec: FacilitySpec,
): { min: Vec3; max: Vec3 } | null {
  const node = index.get(tag);
  if (node !== undefined && index.equipmentTags.includes(tag)) {
    const box = tagBox(node);
    return { min: box.min.toArray(), max: box.max.toArray() };
  }
  const instrument = spec.instruments.find((i) => i.tag === tag);
  return instrument === undefined ? null : instrumentBox(instrument.position_m);
}

/** The index of the mounted station scene, for the real-time layers that find nodes by name. */
export const NodeIndexContext = createContext<NodeIndex | null>(null);

/**
 * Read the node index of the enclosing `StationScene`.
 *
 * @returns The index.
 * @throws Error when used outside a `StationScene`.
 */
export function useNodeIndex(): NodeIndex {
  const index = useContext(NodeIndexContext);
  if (index === null) throw new Error("useNodeIndex outside StationScene");
  return index;
}
