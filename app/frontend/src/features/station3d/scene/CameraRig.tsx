import { CameraControls } from "@react-three/drei";
import { useEffect, useRef, type JSX } from "react";

import { useCameraFlyTo } from "../interaction/useCameraFlyTo";
import { REVIEW_CAMERA } from "./reviewCamera";

const MAX_POLAR_ANGLE_RAD = (85 * Math.PI) / 180;

/**
 * Orbit controls with distance and ground limits, starting at the review camera, plus the
 * fly-to and reset behaviour of {@link useCameraFlyTo}. Mount inside `StationScene`.
 *
 * @returns The camera controls.
 */
export function CameraRig(): JSX.Element {
  const controls = useRef<CameraControls>(null);
  useEffect(() => {
    void controls.current?.setLookAt(...REVIEW_CAMERA.position, ...REVIEW_CAMERA.target, false);
  }, []);
  useCameraFlyTo(controls);
  return <CameraControls ref={controls} makeDefault minDistance={8} maxDistance={350} maxPolarAngle={MAX_POLAR_ANGLE_RAD} />;
}
