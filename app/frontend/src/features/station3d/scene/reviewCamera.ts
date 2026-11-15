import { specToScene, type Vec3 } from "./coords";

/** Spec position the review camera looks at (the K-202 / VS-250 area), in metres. */
export const REVIEW_TARGET_SPEC: Vec3 = [80, 95, 3];

/**
 * The fixed camera used for every screenshot and fps measurement in this project.
 * Position and target are scene coordinates; `fov` is the vertical field of view in degrees.
 */
export const REVIEW_CAMERA = {
  position: specToScene([45, 40, 25]),
  target: specToScene(REVIEW_TARGET_SPEC),
  fov: 35,
} as const;
