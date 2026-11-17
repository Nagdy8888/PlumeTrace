import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef, type JSX } from "react";
import { BufferAttribute, BufferGeometry, Vector3, type Points } from "three";

import { useClockStore } from "@/shared/playback";

import { useNodeIndex } from "../model/nodeIndex";
import { useStationStore } from "../store";
import { createParticleMaterial } from "./plumeMaterial";
import { rateScale, SIGMA_SLOPE, type StabilityClass } from "./plumeMath";
import { gaussianPairs, mulberry32 } from "./random";
import type { PlumeField } from "./usePlumeField";

/** Particle seeds are fixed so a screenshot is reproducible. */
const SEED = 7;
const OFFSET_SEED = 11;
/** Reduced motion slows the drift to a quarter. */
const REDUCED_MOTION_SCALE = 0.25;
const worldPosition = new Vector3();

/** Geometry with `count` particles: zero positions (required by three), gaussian seeds, uniform offsets. */
function buildGeometry(count: number): BufferGeometry {
  const geometry = new BufferGeometry();
  const offsets = new Float32Array(count);
  const rand = mulberry32(OFFSET_SEED);
  for (let i = 0; i < count; i++) offsets[i] = rand();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(count * 3), 3));
  geometry.setAttribute("aSeed", new BufferAttribute(gaussianPairs(count, SEED), 2));
  geometry.setAttribute("aOffset", new BufferAttribute(offsets, 1));
  return geometry;
}

/** Props of {@link PlumeParticles}. */
export interface PlumeParticlesProps {
  /** The plume field. */
  field: PlumeField;
  /** Which of the (at most two) active sources this cloud draws, 0 or 1. */
  sourceIndex: number;
  /** Particles in this cloud. */
  count: number;
  /** Base point size from the quality tier. */
  pointSize: number;
}

/**
 * One GPU particle cloud for one active source. The vertex shader moves the particles along the
 * wind, spreads them by the visual table of the stability class and fades them where the model
 * grid has no gas. The CPU only writes uniforms: time (wall clock, only while playing), source
 * position (the anchor node), wind, spread and brightness. A source whose anchor is not in the
 * station model is not drawn and logged once with a fixed message.
 *
 * @param props - See {@link PlumeParticlesProps}.
 * @returns The points object.
 */
export function PlumeParticles({ field, sourceIndex, count, pointSize }: PlumeParticlesProps): JSX.Element {
  const index = useNodeIndex();
  const points = useRef<Points>(null);
  const reported = useRef(false);
  const geometry = useMemo(() => buildGeometry(count), [count]);
  const { material, uniforms } = useMemo(
    () => createParticleMaterial(field.texA, field.texB, field.rect, pointSize),
    [field, pointSize],
  );
  useEffect(() => () => geometry.dispose(), [geometry]);
  useEffect(() => () => material.dispose(), [material]);
  useFrame((_, delta) => {
    const cloud = points.current;
    if (cloud === null) return;
    const source = field.sources[sourceIndex];
    const node = source === undefined ? undefined : index.get(source.anchor_id);
    if (source !== undefined && node === undefined && !reported.current) {
      reported.current = true;
      console.error("plume source anchor not found in the station model; source not drawn");
    }
    cloud.visible = node !== undefined && source !== undefined;
    if (node === undefined || source === undefined) return;
    if (useClockStore.getState().playing) {
      uniforms.uTime.value += delta * (useStationStore.getState().reducedMotion ? REDUCED_MOTION_SCALE : 1);
    }
    uniforms.uSource.value.copy(node.getWorldPosition(worldPosition));
    uniforms.uToward.value.set(field.towardX, field.towardZ);
    uniforms.uSpeed.value = field.windSpeed;
    const slope = SIGMA_SLOPE[field.stability as StabilityClass] ?? SIGMA_SLOPE.D;
    uniforms.uSigmaSlope.value.set(slope[0], slope[1]);
    uniforms.uMix.value = field.mix;
    uniforms.uRateScale.value = rateScale(source.rate_kg_h);
  });
  return <points ref={points} geometry={geometry} material={material} renderOrder={2} frustumCulled={false} raycast={() => undefined} />;
}
