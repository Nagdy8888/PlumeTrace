import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, type JSX } from "react";
import type { DataTexture, Vector4 } from "three";

import { specToScene } from "../scene/coords";
import { createHeatmapMaterial } from "./heatmapMaterial";

/** What the heat-map needs from the plume field (the field object satisfies it). */
export interface HeatmapField {
  texA: DataTexture;
  texB: DataTexture;
  rect: Vector4;
  mix: number;
}

/** Height of the heat-map above the ground, metres (keeps it off the baked ground plane). */
const LIFT_M = 0.05;

/**
 * The ground heat-map: one plane over the whole site that decodes the two key-frame grids in the
 * fragment shader and draws only cells at or above 1 ppm. It has no raycast, so it never takes
 * a click. `uMix` is written every frame from the field; the grid data is not touched here.
 *
 * @param props - `field`: the plume field.
 * @returns The mesh.
 */
export function GroundHeatmap({ field }: { field: HeatmapField }): JSX.Element {
  const material = useMemo(() => createHeatmapMaterial(field.texA, field.texB), [field.texA, field.texB]);
  useEffect(() => () => material.dispose(), [material]);
  const { x, y, z, w } = field.rect;
  const position = specToScene([x + z / 2, y + w / 2, LIFT_M]);
  useFrame(() => {
    material.uniforms.uMix!.value = field.mix;
  });
  return (
    <mesh
      name="plume-heatmap"
      position={position}
      rotation={[-Math.PI / 2, 0, 0]}
      renderOrder={1}
      material={material}
      raycast={() => undefined}
    >
      <planeGeometry args={[z, w]} />
    </mesh>
  );
}
