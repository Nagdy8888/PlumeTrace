/** Lowest concentration the log-u8 grid encoding can hold (byte 1), in ppm above background. */
export const PPM_MIN = 0.1;
/** Decades the log-u8 encoding spans (0.1 to 1000 ppm). */
export const DECADES = 4;
/** Concentrations below this are not drawn (ppm above background). */
export const DISPLAY_MIN_PPM = 1;
/** Seconds between plume key frames in a replay file. */
export const KEYFRAME_STEP_S = 120;
/** Distance a particle travels from the source before it is recycled, in metres. */
export const MAX_PLUME_DIST_M = 250;

/** Pasquill stability classes that have a spread slope. */
export type StabilityClass = "A" | "B" | "C" | "D" | "E" | "F";

/**
 * Visual spread of the particle cloud per stability class, `(sigma_y / x, sigma_z / x)`.
 *
 * These are Briggs rural near-field slopes at x of about 100 m. They set the SHAPE of the particle
 * cloud only; where gas is drawn is decided by the model grid (see the particle shader), so these
 * numbers never decide a concentration.
 */
export const SIGMA_SLOPE: Record<StabilityClass, readonly [number, number]> = {
  A: [0.22, 0.2],
  B: [0.16, 0.12],
  C: [0.11, 0.08],
  D: [0.08, 0.06],
  E: [0.06, 0.03],
  F: [0.04, 0.016],
};

/**
 * Decode one byte of the backend `log_u8_0.1_1000ppm` grid encoding.
 *
 * @param b - Byte, 0 to 255; 0 means no gas.
 * @returns Concentration in ppm above background: 0 for byte 0, else `0.1 * 10^((b - 1) * 4 / 254)`.
 */
export function decodeLogU8(b: number): number {
  return b === 0 ? 0 : PPM_MIN * 10 ** (((b - 1) * DECADES) / 254);
}

/**
 * Unit vector in scene `(x, z)` that the wind blows TOWARD.
 *
 * Meteorological wind direction is the bearing the wind comes FROM, so it blows toward
 * `fromDeg + 180`. In the facility spec that is `(east, north) = (sin, cos)`; in the scene
 * `x = east` and `z = -north`.
 *
 * @param fromDeg - Wind direction the wind comes from, degrees clockwise from north.
 * @returns `[x, z]` of the unit vector in scene coordinates.
 */
export function windTowardScene(fromDeg: number): [number, number] {
  return windTowardInto(fromDeg, [0, 0]);
}

/**
 * Same as {@link windTowardScene} but writes into a caller-owned pair, so the frame loop
 * allocates nothing.
 *
 * @param fromDeg - Wind direction the wind comes from, degrees clockwise from north.
 * @param out - Pair that receives `[x, z]`.
 * @returns `out`.
 */
export function windTowardInto(fromDeg: number, out: [number, number]): [number, number] {
  const to = ((fromDeg + 180) * Math.PI) / 180;
  out[0] = Math.sin(to);
  out[1] = -Math.cos(to);
  return out;
}

/**
 * Interpolate two compass angles along the shortest arc.
 *
 * @param a - Start angle in degrees.
 * @param b - End angle in degrees.
 * @param f - Fraction from `a` (0) to `b` (1).
 * @returns The angle in `[0, 360)`.
 */
export function lerpAngleDeg(a: number, b: number, f: number): number {
  const delta = ((((b - a) % 360) + 540) % 360) - 180;
  return (((a + delta * f) % 360) + 360) % 360;
}

/** The two key frames around a time and the blend between them (see {@link keyframeInto}). */
export interface KeyframePair {
  /** Earlier key frame index. */
  a: number;
  /** Later key frame index (equals `a` at the last frame). */
  b: number;
  /** Blend from `a` (0) to `b` (1). */
  mix: number;
}

/**
 * Allocation-free {@link keyframeAt}: writes the result into a caller-owned object, so the frame
 * loop allocates nothing.
 *
 * The `mix` is clamped to `[0, 1]`; the clamp only matters for `tSeconds < 0` (owner-ratified
 * deviation from the plan formula).
 *
 * @param tSeconds - Simulation time in seconds.
 * @param count - Number of key frames in the scenario.
 * @param out - Object that receives `a`, `b` and `mix`.
 * @returns `out`.
 */
export function keyframeInto(tSeconds: number, count: number, out: KeyframePair): KeyframePair {
  if (count === 0) {
    out.a = 0;
    out.b = 0;
    out.mix = 0;
    return out;
  }
  const a = Math.min(Math.max(Math.floor(tSeconds / KEYFRAME_STEP_S), 0), count - 1);
  const b = Math.min(a + 1, count - 1);
  const mix = (tSeconds - a * KEYFRAME_STEP_S) / KEYFRAME_STEP_S;
  out.a = a;
  out.b = b;
  out.mix = a === b ? 0 : Math.min(Math.max(mix, 0), 1);
  return out;
}

/**
 * The two key frames around a simulation time and how far between them it is.
 *
 * Allocates one small object; the frame loop uses {@link keyframeInto} instead.
 *
 * @param tSeconds - Simulation time in seconds.
 * @param count - Number of key frames in the scenario.
 * @returns Frame indices `a` and `b` and `mix` in `[0, 1]` (0 when `a === b`).
 */
export function keyframeAt(tSeconds: number, count: number): KeyframePair {
  return keyframeInto(tSeconds, count, { a: 0, b: 0, mix: 0 });
}

/**
 * Opacity scale of the particles for a simulated emission rate; the particle brightness follows
 * the rate but the rate is never shown as a number.
 *
 * @param rateKgH - Simulated rate in kg/h.
 * @returns `rate / 15` clamped to `[0.3, 1]`.
 */
export function rateScale(rateKgH: number): number {
  return Math.min(Math.max(rateKgH / 15, 0.3), 1);
}

/**
 * Heat-map opacity for a concentration (the same law as the fragment shader).
 *
 * @param ppm - Concentration above background, ppm.
 * @returns 0 below the 1 ppm display threshold, else `0.25 + 0.5 * t` (at most 0.75), where `t`
 * is `log10(ppm) / 2` clamped to `[0, 1]`.
 */
export function alphaForPpm(ppm: number): number {
  if (ppm < DISPLAY_MIN_PPM) return 0;
  const t = Math.min(Math.max(Math.log10(ppm) / 2, 0), 1);
  return Math.min(Math.max(0.25 + 0.5 * t, 0), 0.75);
}
