import { specToScene } from "../scene/coords";
import { REVIEW_CAMERA } from "../scene/reviewCamera";

/** A point or vector `[x, y, z]` in scene coordinates (metres). */
export type Vec3 = [number, number, number];

const MIN_DISTANCE_M = 12;
const DISTANCE_PER_SIZE = 2.5;
const ELEVATION_RAD = (30 * Math.PI) / 180;
const FACING_EPS = 1e-6;
const INSTRUMENT_HALF_M = 1;

/**
 * Camera pose for flying to a box: the box centre is the target, the camera keeps its current
 * azimuth around it and looks down at 30 degrees from `max(12, 2.5 * largest dimension)` metres.
 * Directly above the target, the review camera's azimuth (south-west) is used.
 *
 * @param box - World box to frame (scene coordinates).
 * @param cameraPos - Current camera position (scene coordinates).
 * @returns The new camera position and the look-at target.
 */
export function flyToTarget(
  box: { min: Vec3; max: Vec3 },
  cameraPos: Vec3,
): { position: Vec3; target: Vec3 } {
  const target: Vec3 = [
    (box.min[0] + box.max[0]) / 2,
    (box.min[1] + box.max[1]) / 2,
    (box.min[2] + box.max[2]) / 2,
  ];
  const size = Math.max(box.max[0] - box.min[0], box.max[1] - box.min[1], box.max[2] - box.min[2]);
  const distance = Math.max(MIN_DISTANCE_M, DISTANCE_PER_SIZE * size);
  let hx = cameraPos[0] - target[0];
  let hz = cameraPos[2] - target[2];
  if (Math.hypot(hx, hz) < FACING_EPS) {
    hx = REVIEW_CAMERA.position[0] - REVIEW_CAMERA.target[0];
    hz = REVIEW_CAMERA.position[2] - REVIEW_CAMERA.target[2];
  }
  const length = Math.hypot(hx, hz);
  const flat = distance * Math.cos(ELEVATION_RAD);
  return {
    position: [
      target[0] + (hx / length) * flat,
      target[1] + distance * Math.sin(ELEVATION_RAD),
      target[2] + (hz / length) * flat,
    ],
    target,
  };
}

/**
 * A 2 m cube around an instrument, in scene coordinates.
 *
 * @param position_m - Instrument position in the facility spec frame (x east, y north, z up).
 * @returns The box to frame.
 */
export function instrumentBox(position_m: readonly [number, number, number]): { min: Vec3; max: Vec3 } {
  const [x, y, z] = specToScene(position_m);
  return {
    min: [x - INSTRUMENT_HALF_M, y - INSTRUMENT_HALF_M, z - INSTRUMENT_HALF_M],
    max: [x + INSTRUMENT_HALF_M, y + INSTRUMENT_HALF_M, z + INSTRUMENT_HALF_M],
  };
}
