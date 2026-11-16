import { useEffect, useRef, type JSX } from "react";
import type { DirectionalLight } from "three";

import { specToScene, type Vec3 } from "./coords";
import { REVIEW_TARGET_SPEC } from "./reviewCamera";

/** Sun intensity; the owner ruling C2 allows 1.5 to 2.5 (the ground must not read as snow). */
const SUN_INTENSITY = 2.2;

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

/** Props of {@link Sun}: the quality tier decides the shadows. */
export interface SunProps {
  /** Whether the sun casts shadows (off on the low tier). */
  shadows: boolean;
  /** Shadow map edge in pixels (2048 high, 1024 medium, 512 low). */
  mapSize: number;
}

/**
 * The one real-time light: a sun from the HDRI direction (WSW, 18 degrees up) that casts a
 * shadow on the tiers that have shadows.
 *
 * @param props - See {@link SunProps}.
 * @returns The directional light aimed at the review target.
 */
export function Sun({ shadows, mapSize }: SunProps): JSX.Element {
  const light = useRef<DirectionalLight>(null);
  useEffect(() => {
    // The target is not in the scene graph, so its world matrix is set by hand once.
    const aim = light.current?.target;
    if (!aim) return;
    aim.position.set(...TARGET);
    aim.updateMatrixWorld();
  }, []);
  useEffect(() => {
    // A shadow map keeps the size it was created with: drop it so three.js makes a new one.
    const shadow = light.current?.shadow;
    if (!shadow) return;
    shadow.mapSize.set(mapSize, mapSize);
    shadow.map?.dispose();
    shadow.map = null;
  }, [mapSize]);
  return (
    <directionalLight
      ref={light}
      position={POSITION}
      intensity={SUN_INTENSITY}
      color="#ffd7a8"
      castShadow={shadows}
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
