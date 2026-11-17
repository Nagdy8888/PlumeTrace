import type { ReplayScenario } from "@/shared/types/generated/contract";

/**
 * The plume key frames of a scenario, decoded once. The sources are simulation truth that only
 * the plume visual reads (Gate 3 ruling h); they are never shown as text.
 */
export interface PlumeFrames {
  /** Key-frame times in scenario seconds. */
  times: Float64Array;
  /** Grid bytes per frame, `nx * ny`, row-major from the south-west corner. */
  grids: Uint8Array[];
  /** Cells in x. */
  nx: number;
  /** Cells in y. */
  ny: number;
  /** Wind speed per frame, m/s. */
  windSpeed: Float64Array;
  /** Wind direction (the bearing it comes from) per frame, degrees. */
  windFrom: Float64Array;
  /** Pasquill class per frame. */
  stability: string[];
  /** Active sources per frame. */
  sources: { anchor_id: string; rate_kg_h: number }[][];
}

function decodeBase64(b64: string): Uint8Array {
  const text = atob(b64);
  const bytes = new Uint8Array(text.length);
  for (let i = 0; i < text.length; i++) bytes[i] = text.charCodeAt(i);
  return bytes;
}

/**
 * Decode the key frames of a replay scenario (run once per loaded scenario).
 *
 * @param scenario - The loaded replay scenario.
 * @returns The decoded frames (empty arrays when the file has no key frames).
 * @throws Error `plume grid has N bytes, expected nx·ny` when a grid has the wrong size.
 */
export function decodeKeyframes(scenario: ReplayScenario): PlumeFrames {
  const { nx, ny } = scenario.grid;
  const frames = scenario.keyframes;
  const grids = frames.map((frame) => {
    const bytes = decodeBase64(frame.grid_b64);
    if (bytes.length !== nx * ny) throw new Error(`plume grid has ${bytes.length} bytes, expected ${nx * ny}`);
    return bytes;
  });
  return {
    times: Float64Array.from(frames, (f) => f.t_s),
    grids,
    nx,
    ny,
    windSpeed: Float64Array.from(frames, (f) => f.wind_speed_m_s),
    windFrom: Float64Array.from(frames, (f) => f.wind_from_deg),
    stability: frames.map((f) => f.stability),
    sources: frames.map((f) => f.sources.map((s) => ({ anchor_id: s.anchor_id, rate_kg_h: s.rate_kg_h }))),
  };
}
