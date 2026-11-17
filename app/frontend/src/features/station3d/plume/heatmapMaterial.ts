import { NormalBlending, ShaderMaterial, type DataTexture } from "three";

import { RAMP_TOKENS, readTokenColor } from "./plumeColors";
import { HEATMAP_FRAGMENT, HEATMAP_VERTEX } from "./plumeShaders";

/**
 * Material of the ground heat-map: two grid textures blended by `uMix`, coloured on the five
 * methane ramp tokens, transparent and without depth writes.
 *
 * @param texA - Grid of the earlier key frame.
 * @param texB - Grid of the later key frame.
 * @returns A new `ShaderMaterial` (the caller disposes it).
 */
export function createHeatmapMaterial(texA: DataTexture, texB: DataTexture): ShaderMaterial {
  const [r0, r1, r2, r3, r4] = RAMP_TOKENS.map(readTokenColor);
  return new ShaderMaterial({
    vertexShader: HEATMAP_VERTEX,
    fragmentShader: HEATMAP_FRAGMENT,
    uniforms: {
      uGridA: { value: texA },
      uGridB: { value: texB },
      uMix: { value: 0 },
      uRamp0: { value: r0 },
      uRamp1: { value: r1 },
      uRamp2: { value: r2 },
      uRamp3: { value: r3 },
      uRamp4: { value: r4 },
    },
    transparent: true,
    depthWrite: false,
    blending: NormalBlending,
  });
}
