/** Rendering quality tiers (frontend-3d rule 6). */
export type QualityTier = "high" | "medium" | "low";

/** Per-tier canvas settings. Plume counts are used by Task 9. */
export const QUALITY: Record<QualityTier, { dpr: [number, number]; shadows: boolean; shadowMapSize: number; plumeParticles: number }> = {
  high: { dpr: [1, 1.5], shadows: true, shadowMapSize: 2048, plumeParticles: 40000 },
  medium: { dpr: [1, 1.25], shadows: true, shadowMapSize: 1024, plumeParticles: 20000 },
  low: { dpr: [1, 1], shadows: false, shadowMapSize: 512, plumeParticles: 10000 },
};
