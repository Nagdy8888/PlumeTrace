import { Bloom, EffectComposer, SMAA } from "@react-three/postprocessing";
import type { JSX } from "react";

import type { QualityTier } from "./qualitySettings";

/**
 * Post-processing: bloom that picks up only what is brighter than 1 (the flare flame and the
 * candidate glow; the rest of the scene stays below the threshold) and SMAA anti-aliasing. It is
 * mounted on `high` and `medium` and not at all on `low`. No vignette, grain or colour fringing.
 *
 * @param props - `tier`: the quality tier in force.
 * @returns The effect composer, or nothing on the low tier.
 */
export function PostEffects({ tier }: { tier: QualityTier }): JSX.Element | null {
  if (tier === "low") return null;
  return (
    <EffectComposer multisampling={0}>
      <Bloom luminanceThreshold={1} mipmapBlur intensity={0.6} />
      <SMAA />
    </EffectComposer>
  );
}
