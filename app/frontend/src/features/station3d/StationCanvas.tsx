import { Canvas } from "@react-three/fiber";
import { Suspense, type JSX } from "react";

import { PerfOverlay } from "./dev/PerfOverlay";
import { StationModel } from "./model/StationModel";
import { EnvironmentMap } from "./scene/EnvironmentMap";
import { REVIEW_CAMERA } from "./scene/reviewCamera";
import { Sun } from "./scene/Sun";

/** `?perf` in the URL turns the measuring overlay on (dev builds only). */
const SHOW_PERF = new URLSearchParams(window.location.search).has("perf");

/**
 * The R3F canvas: review camera, local image-based lighting, one shadow-casting sun and the
 * baked station model. Everything dynamic (plume, highlights) arrives in later tasks.
 *
 * @returns The canvas filling its parent.
 */
export default function StationCanvas(): JSX.Element {
  return (
    <Canvas
      dpr={[1, 1.5]}
      shadows
      camera={{ position: REVIEW_CAMERA.position, fov: REVIEW_CAMERA.fov, near: 0.5, far: 2000 }}
      gl={{ antialias: true }}
      onCreated={({ camera }) => camera.lookAt(...REVIEW_CAMERA.target)}
    >
      <Suspense fallback={null}>
        <EnvironmentMap />
        <Sun />
        <StationModel />
      </Suspense>
      {SHOW_PERF && <PerfOverlay />}
    </Canvas>
  );
}
