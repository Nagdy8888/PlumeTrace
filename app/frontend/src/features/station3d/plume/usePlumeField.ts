import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo } from "react";
import { DataTexture, NearestFilter, RedFormat, UnsignedByteType, Vector4 } from "three";

import { useClockStore } from "@/shared/playback";
import type { ReplayScenario } from "@/shared/types/generated/contract";

import { decodeKeyframes, type PlumeFrames } from "./plumeFrames";
import { type KeyframePair, keyframeInto, lerpAngleDeg, windTowardInto } from "./plumeMath";

/** The plume state for the current clock time. One object, mutated every frame, never replaced. */
export interface PlumeField {
  /** Decoded key frames of the scenario. */
  frames: PlumeFrames;
  /** Grid texture of the earlier key frame. */
  texA: DataTexture;
  /** Grid texture of the later key frame. */
  texB: DataTexture;
  /** Grid rectangle `(x0, y0, width, height)` in spec metres. */
  rect: Vector4;
  /** Blend from `texA` (0) to `texB` (1). */
  mix: number;
  /** Interpolated wind speed, m/s. */
  windSpeed: number;
  /** Scene x of the unit vector the wind blows toward. */
  towardX: number;
  /** Scene z of the unit vector the wind blows toward. */
  towardZ: number;
  /** Pasquill class of the earlier key frame. */
  stability: string;
  /** Active sources of the earlier key frame (drawing only; never shown as text). */
  sources: PlumeFrames["sources"][number];
  /** Key frame currently in `texA`, or -1. */
  frameA: number;
  /** Key frame currently in `texB`, or -1. */
  frameB: number;
}

const NO_SOURCES: PlumeFrames["sources"][number] = [];
const toward: [number, number] = [0, 0];
const pair: KeyframePair = { a: 0, b: 0, mix: 0 };

function gridTexture(nx: number, ny: number): DataTexture {
  const texture = new DataTexture(new Uint8Array(nx * ny), nx, ny, RedFormat, UnsignedByteType);
  texture.magFilter = NearestFilter;
  texture.minFilter = NearestFilter;
  texture.unpackAlignment = 1;
  texture.needsUpdate = true;
  return texture;
}

/** Copy a frame's bytes into a texture's own buffer (no allocation) and flag the upload. */
function load(texture: DataTexture, bytes: Uint8Array | undefined): void {
  if (bytes === undefined) return;
  (texture.image.data as Uint8Array).set(bytes);
  texture.needsUpdate = true;
}

/** Update the field in place for clock time `t`. Allocation free. */
function update(field: PlumeField, t: number): void {
  const { frames } = field;
  const { a, b, mix } = keyframeInto(t, frames.times.length, pair);
  if (frames.times.length === 0) return;
  if (a !== field.frameA) {
    load(field.texA, frames.grids[a]);
    field.frameA = a;
    field.sources = frames.sources[a] ?? NO_SOURCES;
    field.stability = frames.stability[a] ?? "D";
  }
  if (b !== field.frameB) {
    load(field.texB, frames.grids[b]);
    field.frameB = b;
  }
  const from = lerpAngleDeg(frames.windFrom[a] ?? 0, frames.windFrom[b] ?? 0, mix);
  windTowardInto(from, toward);
  field.mix = mix;
  field.towardX = toward[0];
  field.towardZ = toward[1];
  const speedA = frames.windSpeed[a] ?? 0;
  field.windSpeed = speedA + ((frames.windSpeed[b] ?? 0) - speedA) * mix;
}

/**
 * Build the plume field of a scenario: the decoded key frames, two grid textures created once,
 * and a per-frame update that follows the SIMULATION clock. A frame's bytes are copied into a
 * texture only when the key frame index changes. The frame loop allocates nothing and sets no
 * React state. Sources are read for drawing only; this module never turns them into text.
 *
 * @param scenario - The loaded replay scenario.
 * @returns The stable, mutated field object.
 * @throws Error when a key-frame grid has the wrong size (from `decodeKeyframes`).
 */
export function usePlumeField(scenario: ReplayScenario): PlumeField {
  const field = useMemo<PlumeField>(() => {
    const frames = decodeKeyframes(scenario);
    const { x0_m, y0_m, dx_m, dy_m, nx, ny } = scenario.grid;
    return {
      frames,
      texA: gridTexture(nx, ny),
      texB: gridTexture(nx, ny),
      rect: new Vector4(x0_m, y0_m, nx * dx_m, ny * dy_m),
      mix: 0,
      windSpeed: 0,
      towardX: 1,
      towardZ: 0,
      stability: "D",
      sources: NO_SOURCES,
      frameA: -1,
      frameB: -1,
    };
  }, [scenario]);
  useEffect(
    () => () => {
      field.texA.dispose();
      field.texB.dispose();
    },
    [field],
  );
  // priority -1: the field is current before the layers that read it draw
  useFrame(() => update(field, useClockStore.getState().tSeconds), -1);
  return field;
}
