import type { ThreeEvent } from "@react-three/fiber";
import { useMemo, type JSX } from "react";
import { BoxGeometry, MeshBasicMaterial, Vector3 } from "three";

import { useSelectionStore } from "@/shared/selection";

import { tagBox, type NodeIndex } from "./nodeIndex";

/** One unit box and one invisible material, shared by every proxy (never disposed: they outlive the scene). */
const UNIT_BOX = new BoxGeometry(1, 1, 1);
const HIT_MATERIAL = new MeshBasicMaterial({ colorWrite: false, depthWrite: false });
/** A flat box would have a singular matrix and could not be raycast. */
const MIN_SIZE_M = 0.1;

interface Proxy {
  tag: string;
  position: [number, number, number];
  scale: [number, number, number];
}

function buildProxies(index: NodeIndex): Proxy[] {
  return index.equipmentTags.flatMap((tag) => {
    const node = index.get(tag);
    if (node === undefined) return [];
    const box = tagBox(node);
    const size = box.getSize(new Vector3()).toArray().map((m) => Math.max(m, MIN_SIZE_M));
    return [{ tag, position: box.getCenter(new Vector3()).toArray(), scale: size as Proxy["scale"] }];
  });
}

function stop(event: ThreeEvent<PointerEvent | MouseEvent>): void {
  event.stopPropagation();
}

/**
 * One invisible box per equipment item; the only objects that receive pointer events (the baked
 * meshes have no-op raycasts). Hover and click go to the selection store.
 *
 * @param props - `index`: the station node index. The root must have an identity transform, so
 * a node's world box is also its place in scene coordinates.
 * @returns The proxies.
 */
export function HitProxies({ index }: { index: NodeIndex }): JSX.Element {
  const proxies = useMemo(() => buildProxies(index), [index]);
  return (
    <>
      {proxies.map(({ tag, position, scale }) => (
        <mesh
          key={tag}
          name={`${tag}__hit`}
          geometry={UNIT_BOX}
          material={HIT_MATERIAL}
          position={position}
          scale={scale}
          onPointerOver={(e) => {
            stop(e);
            useSelectionStore.getState().hover(tag);
            document.body.style.cursor = "pointer";
          }}
          onPointerOut={(e) => {
            stop(e);
            useSelectionStore.getState().hover(null);
            document.body.style.cursor = "";
          }}
          onClick={(e) => {
            stop(e);
            useSelectionStore.getState().select(tag);
          }}
        />
      ))}
    </>
  );
}
