# Performance and testing

## Canvas setup (`StationCanvas.tsx`)
- `dpr` from the quality tier (cap `[1, 1.5]`); `gl={{ antialias: false, powerPreference: "high-performance" }}`
  when SMAA runs in postprocessing; `shadows` only on medium/high.
- `frameloop`: `"always"` while the simulation/replay is playing (plume moves); `"demand"` when
  paused, calling `invalidate()` on interaction (drei controls do this automatically).
- drei `PerformanceMonitor`: `onDecline` → drop one quality tier; `onIncline` → raise one tier
  (with hysteresis); `AdaptiveDpr` optional.
- Wrap scene content in `Suspense` with a lightweight placeholder; lazy-load the whole
  `StationCanvas` from `StationView` so the 2D panels render first.

## R3F pitfalls (from the R3F docs — verify against the pinned version)
- Never `setState` in `useFrame`; mutate refs.
- Never allocate in the frame loop (`new Vector3`, `.clone()`); keep module-level temporaries.
  `@react-three/eslint-plugin` rules `no-new-in-loop` and `no-clone-in-loop` must be on.
- Don't mount/unmount meshes to show/hide — toggle `visible`.
- Reuse geometries/materials; prefer instancing and merged geometry for repeated parts.
- Avoid many lights; use one directional light + IBL; bake what you can.
- Keep `Html` overlays few; they are DOM elements updated every frame.

## Measuring
- Dev only: `r3f-perf` or drei `Stats` (never in the production bundle).
- Log `gl.info.render.calls`, `gl.info.render.triangles`, `gl.info.memory` at the review camera
  after each feature; record them in `docs/WORK_LOG.md`.
- fps: Playwright script that loads the review camera, plays scenario S1 for 10 s and reads
  average frame time from a `requestAnimationFrame` sampler exposed in dev builds; record the
  hardware. Target ≥ 58 fps average at 1080p "high" on integrated graphics.
- Bundle: three.js tree-shaking via named imports; check the 3D chunk size in `vite build`
  output; the 3D chunk loads after first paint.

## Testing
- **Scene-graph tests** with `@react-three/test-renderer` (Vitest):
  - `SiteLayout` renders one equipment group per spec item, with the right tags.
  - Instanced components create the expected instance counts from the spec.
  - Picking: `fireEvent(hitProxy, "click")` sets the selection in the store.
  - Animation: `advanceFrames(n, delta)` moves fan blades / plume uniforms as expected.
- **Visual tests** with Playwright: fixed review camera, fixed seed and time, quality "high",
  screenshot compared with a stored baseline (tolerance set, baseline updates reviewed by a human).
- **Fallback tests:** WebGL unavailable → static image + equipment list; reduced motion → no
  fly-to animation.
- Tests never depend on GPU timing; fps checks are a separate, recorded measurement.
