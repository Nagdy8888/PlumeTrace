# Plume and effects

## Input: the plume field (never computed in the frontend)
The backend sends, per time step, a **plume field**: source anchor id, emission rate (kg/h),
wind speed/direction, stability class, and a downwind grid of concentration (ppm above
background) or the plume parameters (σy, σz per distance). `usePlumeField.ts` reads it from the
active data source (live or replay) into a ref, and interpolates between steps. The frontend only
maps these numbers to visuals.

## Plume particles (`PlumeParticles.tsx`, `plumeMaterial.ts`, `plumeShaders.ts`)
- One `THREE.Points` (or instanced quads) with a custom `ShaderMaterial`; positions advected on
  the GPU in the vertex shader from per-particle seed + age + uniforms (wind vector, σ growth,
  source position). No per-particle CPU loop per frame.
- Uniforms updated in `useFrame` by mutation: `uTime`, `uWind`, `uSource`, `uRateScale`,
  `uSigmaY`, `uSigmaZ`. Spawn rate and opacity scale with emission rate; spread follows σy/σz.
- Additive or premultiplied alpha blending, `depthWrite={false}`, soft round sprite from a local
  texture or computed in the fragment shader. Colour: desaturated warm-grey methane tint (methane
  is invisible — the overlay is a visualisation, labelled as such in the legend), shifting to the
  alarm accent where concentration exceeds the alarm threshold.
- Particle count from the quality tier (≤ 40 k high, ≤ 10 k low). Pause advection when the
  simulation is paused.

## Ground heat-map (`GroundHeatmap.tsx`)
- A ground-aligned plane with a `DataTexture` (Float or RGBA8) built from the concentration grid,
  mapped through a colour ramp texture (perceptually uniform, colour-blind safe); update the
  texture data in place and set `needsUpdate` — never recreate it per frame.
- Legend in the 2D UI with units (ppm) and the alarm threshold.

## Other overlays
- **Wind indicator:** windsock at the met mast plus a ground arrow; direction and length from
  the met data.
- **Sensor markers:** small posts at sensor positions; ring pulses when a reading crosses the
  threshold (event-driven, not continuous).
- **Candidate highlight:** outline/glow on the components the inversion ranked, strength
  proportional to posterior probability; the top candidate gets the label "K-202 rod packing 87%"
  (numbers straight from the tool result).
- **Tag labels:** drei `Html` or SDF text with a **local font file**; only for selected/hovered
  items and candidates (labels for everything kill performance and readability).
- **Flare flame:** animated emissive cone/billboard with flicker in the shader; off when pilot is
  out; heat shimmer only on "high".

## Postprocessing (`PostEffects.tsx`)
- `@react-three/postprocessing` `EffectComposer` with: selective Bloom (flare, alarm beacons,
  candidate glow only — use emissive intensity > 1 / luminance threshold), SMAA, optional AO on
  "high". Disable the composer entirely on "low".
- No vignette/film grain/chromatic aberration — it reads as a game, not an HMI.

## Camera (`CameraRig.tsx`, `useCameraFlyTo.ts`)
- drei `CameraControls`: orbit with limits (no going under the ground, min/max distance, polar
  angle limits). Default review camera is a fixed, documented position used for screenshots.
- Fly-to: when the agents locate a source, `setLookAt(..., true)` to the anchor with a short
  eased transition; with reduced motion, jump without animation.
- Idle auto-orbit only on the landing view, stops on any interaction.
