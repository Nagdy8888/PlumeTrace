import { useEffect, useRef, type JSX } from "react";
import type { DirectionalLight } from "three";

import { specToScene, type Vec3 } from "./coords";
import { REVIEW_TARGET_SPEC } from "./reviewCamera";

const AZIMUTH_DEG = 250; // compass bearing of the sun: WSW
const ELEVATION_DEG = 18;
const DISTANCE_M = 150;
const SHADOW_EXTENT_M = 60;

/** Spec-space position of the sun: `target + 150 m` towards (azimuth, elevation). */
function sunSpecPosition(target: Vec3): Vec3 {
  const az = (AZIMUTH_DEG * Math.PI) / 180;
  const el = (ELEVATION_DEG * Math.PI) / 180;
  return [
    target[0] + DISTANCE_M * Math.sin(az) * Math.cos(el),
    target[1] + DISTANCE_M * Math.cos(az) * Math.cos(el),
    target[2] + DISTANCE_M * Math.sin(el),
  ];
}

const TARGET = specToScene(REVIEW_TARGET_SPEC);
const POSITION = specToScene(sunSpecPosition(REVIEW_TARGET_SPEC));

/**
 * The one real-time light: a shadow-casting sun from the HDRI direction (WSW, 18 degrees up).
 *
 * @returns The directional light aimed at the review target.
 */
export function Sun(): JSX.Element {
  const light = useRef<DirectionalLight>(null);
  useEffect(() => {
    // The target is not in the scene graph, so its world matrix is set by hand once.
    const aim = light.current?.target;
    if (!aim) return;
    aim.position.set(...TARGET);
    aim.updateMatrixWorld();
  }, []);
  return (
    <directionalLight
      ref={light}
      position={POSITION}
      intensity={2.5}
      color="#ffd7a8"
      castShadow
      shadow-mapSize={[2048, 2048]}
      shadow-camera-left={-SHADOW_EXTENT_M}
      shadow-camera-right={SHADOW_EXTENT_M}
      shadow-camera-top={SHADOW_EXTENT_M}
      shadow-camera-bottom={-SHADOW_EXTENT_M}
      shadow-camera-near={1}
      shadow-camera-far={400}
      shadow-bias={-0.0005}
    />
  );
}
