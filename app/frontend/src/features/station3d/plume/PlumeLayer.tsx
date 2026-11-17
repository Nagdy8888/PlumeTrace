import type { JSX } from "react";

import { useClockStore } from "@/shared/playback";
import type { ReplayScenario } from "@/shared/types/generated/contract";

import { QUALITY } from "../scene/qualitySettings";
import { useQualityTier } from "../store";
import { GroundHeatmap } from "./GroundHeatmap";
import { type KeyframePair, keyframeInto } from "./plumeMath";
import { PlumeParticles } from "./PlumeParticles";
import { usePlumeField } from "./usePlumeField";

/** At most this many sources are drawn; the particle budget is split between them. */
const MAX_DRAWN_SOURCES = 2;
/** Base point size per tier: 1.6 on high (more, smaller particles), 2.0 on medium and low. */
const POINT_SIZE = { high: 1.6, medium: 2.0, low: 2.0 } as const;
/** Scratch for the clock-store selector below (it runs on every clock update; no allocation). */
const pair: KeyframePair = { a: 0, b: 0, mix: 0 };

/**
 * The plume of the active scenario: the ground heat-map and one particle cloud per active source
 * (at most two). All of it is driven by the model grid and the simulation clock; the layer
 * re-renders only when the number of active sources changes (a key frame boundary), never per
 * animation frame. Nothing here draws text.
 *
 * @param props - `scenario`: the loaded replay scenario.
 * @returns The heat-map and the particle clouds.
 */
export function PlumeLayer({ scenario }: { scenario: ReplayScenario }): JSX.Element {
  const field = usePlumeField(scenario);
  const tier = useQualityTier();
  const frameCount = field.frames.times.length;
  const active = useClockStore((s) =>
    Math.min(field.frames.sources[keyframeInto(s.tSeconds, frameCount, pair).a]?.length ?? 0, MAX_DRAWN_SOURCES),
  );
  const perSource = active === 0 ? 0 : Math.floor(QUALITY[tier].plumeParticles / active);
  return (
    <>
      <GroundHeatmap field={field} />
      {Array.from({ length: active }, (_, i) => (
        <PlumeParticles key={i} field={field} sourceIndex={i} count={perSource} pointSize={POINT_SIZE[tier]} />
      ))}
    </>
  );
}
