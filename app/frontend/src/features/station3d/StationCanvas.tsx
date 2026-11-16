import { PerformanceMonitor } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense, type JSX } from "react";

import { useClockStore } from "@/shared/playback";

import { PerfOverlay } from "./dev/PerfOverlay";
import { StationModel } from "./model/StationModel";
import { CameraRig } from "./scene/CameraRig";
import { EnvironmentMap } from "./scene/EnvironmentMap";
import { QUALITY } from "./scene/qualitySettings";
import { REVIEW_CAMERA } from "./scene/reviewCamera";
import { Sun } from "./scene/Sun";
import { useQualityTier, useStationStore } from "./store";

/** `?perf` in the URL turns the measuring overlay on (dev builds only). */
const SHOW_PERF = new URLSearchParams(window.location.search).has("perf");

/**
 * The R3F canvas: quality tier (dpr, shadows), review camera and orbit controls, local
 * image-based lighting, one sun and the baked station. It renders every frame while the clock is
 * playing and on demand otherwise. While the clock plays, the frame-rate monitor lowers the
 * automatic tier one step per decline; it never changes or stores the manual choice. The plume and
 * highlights arrive in Task 9.
 *
 * @returns The canvas filling its parent.
 */
export default function StationCanvas(): JSX.Element {
  const tier = useQualityTier();
  const playing = useClockStore((s) => s.playing);
  const decline = useStationStore((s) => s.decline);
  const settings = QUALITY[tier];
  return (
    <Canvas
      frameloop={playing ? "always" : "demand"}
      dpr={settings.dpr}
      shadows={settings.shadows}
      gl={{ antialias: true, powerPreference: "high-performance" }}
      camera={{ fov: REVIEW_CAMERA.fov, near: 0.5, far: 2000, position: REVIEW_CAMERA.position }}
    >
      {/* on-demand frames are sparse and would read as a low frame rate; measure only while playing */}
      {playing && <PerformanceMonitor onDecline={decline} />}
      <Suspense fallback={null}>
        <EnvironmentMap />
        <Sun shadows={settings.shadows} mapSize={settings.shadowMapSize} />
        <StationModel>
          <CameraRig />
        </StationModel>
      </Suspense>
      {SHOW_PERF && <PerfOverlay />}
    </Canvas>
  );
}
