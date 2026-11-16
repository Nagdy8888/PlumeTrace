import type { CameraControls } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import { useEffect, type RefObject } from "react";

import { useSelectionStore } from "@/shared/selection";

import { FACILITY } from "../model/facility";
import { tagBounds, useNodeIndex } from "../model/nodeIndex";
import { REVIEW_CAMERA } from "../scene/reviewCamera";
import { RESET_VIEW_EVENT, useStationStore } from "../store";
import { flyToTarget } from "./flyToTarget";

/** Keys that keep their own meaning (typing, native lists). */
const OWN_KEYS = "input, select, textarea, [contenteditable]";

/** Fly (or, with reduced motion, jump) unless the viewer asked for less motion. */
function animate(): boolean {
  return !useStationStore.getState().reducedMotion;
}

/**
 * Camera moves of the station view. Selecting a tag flies the camera to it (`flyToTarget`: its
 * azimuth is kept, 30 degrees elevation); `R` and the `plumetrace:reset-view` event return to the
 * review camera. With `prefers-reduced-motion` the camera jumps instead of flying. An unknown
 * tag is ignored. Must be mounted inside `StationScene` (it needs the node index).
 *
 * @param controls - Ref of the drei `CameraControls`.
 */
export function useCameraFlyTo(controls: RefObject<CameraControls | null>): void {
  const index = useNodeIndex();
  const camera = useThree((s) => s.camera);
  const selectedTag = useSelectionStore((s) => s.selectedTag);

  useEffect(() => {
    if (selectedTag === null || controls.current === null) return;
    const bounds = tagBounds(selectedTag, index, FACILITY);
    if (bounds === null) return;
    const { position, target } = flyToTarget(bounds, [camera.position.x, camera.position.y, camera.position.z]);
    void controls.current.setLookAt(...position, ...target, animate());
  }, [selectedTag, index, camera, controls]);

  useEffect(() => {
    const reset = (): void => {
      void controls.current?.setLookAt(...REVIEW_CAMERA.position, ...REVIEW_CAMERA.target, animate());
    };
    const onKey = (event: KeyboardEvent): void => {
      if (event.code !== "KeyR" || event.ctrlKey || event.metaKey || event.altKey) return;
      if (event.target instanceof Element && event.target.closest(OWN_KEYS)) return;
      reset();
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener(RESET_VIEW_EVENT, reset);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener(RESET_VIEW_EVENT, reset);
    };
  }, [controls]);
}
