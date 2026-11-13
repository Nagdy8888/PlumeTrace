# Phase 4 · Task 9 — Plume particles, ground heat-map, sensors, windsock, flare, candidate highlight

**Skills:** `plan-execution`, `frontend-3d` (+ `references/plume-and-effects.md`, `performance-and-testing.md`), `dataviz` (ramp + legend), `project-documentation`.
**Docs to check first (Context7):** three 0.187.0 (`ShaderMaterial`, `DataTexture`, `RedFormat`, `UnsignedByteType`, `Points`, `BufferAttribute`, WebGL2 shader conversion of `texture2D` / `gl_FragColor`), @react-three/postprocessing 3.2.2 (`EffectComposer`, `Bloom`, `SMAA`), drei `Billboard`.

**Rule (frontend-3d rule 2):** where the gas is comes only from the replay's plume key frames (the
model grid). The particle *shape* uses a small visual spread table; particle *visibility* is
gated by the model grid, so nothing is drawn where the model has no gas.

## Fixed decisions
- Key frames every 120 s (`scenario.keyframes`), grid 40 × 30 cells of 5 m from (0, 0) — the whole site — encoding `log_u8_0.1_1000ppm` (decode: `0 → 0`; `b → 0.1 · 10^((b − 1) · 4 / 254)` ppm).
- Between key frames the two grids are blended in the shader (`uMix`); wind direction is interpolated along the shortest arc.
- Particles move at the real wind speed in **wall-clock** seconds while playing (so they look physical at any playback speed); they freeze when paused. The field follows **simulation** time.
- Display threshold 1 ppm above background; ramp from 1 ppm (`--ch4-0`) to 100 ppm+ (`--ch4-4`), log scale.
- At most 2 active sources are drawn; particle budget per tier from `QUALITY[tier].plumeParticles`, split evenly.
- `CandidateHighlight` is built and tested here but mounted in Phase 5 (it needs inversion results).

## Files (`app/frontend/src/features/station3d/` unless noted)
| Action | Path |
|---|---|
| Modify | `app/frontend/package.json` → `"@react-three/postprocessing": "3.2.2"`, `"postprocessing": "6.39.6"` |
| Create (pure) | `plume/plumeMath.ts`, `plume/plumeMath.test.ts`, `plume/plumeFrames.ts`, `plume/plumeFrames.test.ts`, `plume/random.ts` |
| Create | `plume/plumeShaders.ts`, `plume/heatmapMaterial.ts`, `plume/plumeMaterial.ts`, `plume/usePlumeField.ts`, `plume/GroundHeatmap.tsx`, `plume/PlumeParticles.tsx`, `plume/PlumeLayer.tsx`, `plume/PlumeLayer.test.tsx`, `plume/PlumeLegend.tsx` (DOM) |
| Create | `overlays/SensorMarkers.tsx`, `overlays/SensorMarkers.test.tsx`, `overlays/WindSock.tsx`, `overlays/FlareFlame.tsx`, `overlays/CandidateHighlight.tsx`, `overlays/CandidateHighlight.test.tsx`, `scene/PostEffects.tsx` |
| Modify | `model/StationScene.tsx` (mount plume layer, sensors, windsock, flare), `StationCanvas.tsx` (post effects), `StationView.tsx` (legend overlay) |

## Pure helpers
`plume/plumeMath.ts`:
- `PPM_MIN = 0.1`, `DECADES = 4`, `DISPLAY_MIN_PPM = 1`, `KEYFRAME_STEP_S = 120`, `MAX_PLUME_DIST_M = 250`.
- `decodeLogU8(b: number): number` — as above.
- `windTowardScene(fromDeg: number): [number, number]` — unit vector in scene `(x, z)` the wind blows **toward**: `to = fromDeg + 180`; spec `(east, north) = (sin(to), cos(to))`; scene `(x, z) = (east, −north)`.
- `lerpAngleDeg(a: number, b: number, f: number): number` — shortest arc, result in `[0, 360)`.
- `keyframeAt(tSeconds: number, count: number): { a: number; b: number; mix: number }` — `a = clamp(floor(t / 120), 0, count − 1)`, `b = min(a + 1, count − 1)`, `mix = a === b ? 0 : (t − a·120) / 120`; `count === 0` → `{ a: 0, b: 0, mix: 0 }`.
- `rateScale(rateKgH: number): number` — `clamp(rate / 15, 0.3, 1)`.
- `SIGMA_SLOPE: Record<"A"|"B"|"C"|"D"|"E"|"F", [number, number]>` — `(σy/x, σz/x)`: A `[0.22, 0.20]`, B `[0.16, 0.12]`, C `[0.11, 0.08]`, D `[0.08, 0.06]`, E `[0.06, 0.03]`, F `[0.04, 0.016]` (Briggs rural near-field slopes at x ≈ 100 m; **shape only** — TSDoc says so).
- `alphaForPpm(ppm: number): number` — `ppm < 1 → 0`; else `t = clamp(log10(ppm) / 2, 0, 1)`, return `clamp(0.25 + 0.5·t, 0, 0.75)`.

`plume/plumeFrames.ts`:
- `interface PlumeFrames { times: Float64Array; grids: Uint8Array[]; nx: number; ny: number; windSpeed: Float64Array; windFrom: Float64Array; stability: string[]; sources: { anchor_id: string; rate_kg_h: number }[][] }`
- `decodeKeyframes(scenario: ReplayScenario): PlumeFrames` — base64 via `atob` into `Uint8Array` per frame; throws `Error("plume grid has N bytes, expected nx·ny")` on a size mismatch. Run once per loaded scenario (`useMemo` on the scenario object).

`plume/random.ts`: `mulberry32(seed: number): () => number` and `gaussianPairs(n: number, seed: number): Float32Array` (Box–Muller, `2n` values) — particle seeds are deterministic (seed 7) so screenshots are reproducible.

## Shaders (`plume/plumeShaders.ts`, exported string constants; full code)
Shared decode function, prefixed to both shaders that sample the grid:
```glsl
float decodePpm(float b) {
  float v = floor(b * 255.0 + 0.5);
  if (v < 0.5) return 0.0;
  return 0.1 * pow(10.0, (v - 1.0) * 4.0 / 254.0);
}
float gridPpm(sampler2D a, sampler2D b, float m, vec2 uv) {
  return mix(decodePpm(texture2D(a, uv).r), decodePpm(texture2D(b, uv).r), m);
}
```
(Grid textures use `NearestFilter` so decoding never mixes two encoded bytes; smoothness comes from the 5 m cells being small on screen and from `uMix`.)

Heat-map vertex:
```glsl
varying vec2 vUv;
void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
```
Heat-map fragment:
```glsl
uniform sampler2D uGridA;
uniform sampler2D uGridB;
uniform float uMix;
uniform vec3 uRamp0; uniform vec3 uRamp1; uniform vec3 uRamp2; uniform vec3 uRamp3; uniform vec3 uRamp4;
varying vec2 vUv;
vec3 ramp(float t) {
  float s = clamp(t, 0.0, 1.0) * 4.0;
  if (s < 1.0) return mix(uRamp0, uRamp1, s);
  if (s < 2.0) return mix(uRamp1, uRamp2, s - 1.0);
  if (s < 3.0) return mix(uRamp2, uRamp3, s - 2.0);
  return mix(uRamp3, uRamp4, s - 3.0);
}
void main() {
  float ppm = gridPpm(uGridA, uGridB, uMix, vUv);
  if (ppm < 1.0) discard;
  float t = clamp(log(ppm) / log(10.0) / 2.0, 0.0, 1.0);
  gl_FragColor = vec4(ramp(t), clamp(0.25 + 0.5 * t, 0.0, 0.75));
}
```
Particle vertex:
```glsl
attribute vec2 aSeed;
attribute float aOffset;
uniform float uTime;
uniform vec3 uSource;
uniform vec2 uToward;
uniform float uSpeed;
uniform float uMaxDist;
uniform vec2 uSigmaSlope;
uniform sampler2D uGridA;
uniform sampler2D uGridB;
uniform float uMix;
uniform vec4 uGridRect;
uniform float uRateScale;
uniform float uPointSize;
varying float vAlpha;
void main() {
  float life = uMaxDist / max(uSpeed, 0.5);
  float age = fract(uTime / life + aOffset);
  float d = age * uMaxDist;
  vec2 side = vec2(-uToward.y, uToward.x);
  vec3 p = uSource;
  p.xz += uToward * d + side * aSeed.x * uSigmaSlope.x * (d + 2.0);
  p.y = max(0.1, p.y + aSeed.y * uSigmaSlope.y * (d + 2.0));
  vec2 uv = vec2((p.x - uGridRect.x) / uGridRect.z, (-p.z - uGridRect.y) / uGridRect.w);
  float ppm = 0.0;
  if (uv.x >= 0.0 && uv.x <= 1.0 && uv.y >= 0.0 && uv.y <= 1.0) ppm = gridPpm(uGridA, uGridB, uMix, uv);
  float t = clamp(log(max(ppm, 0.01)) / log(10.0) / 2.0, 0.0, 1.0);
  float nearSource = 1.0 - smoothstep(5.0, 15.0, d);
  float fromGrid = ppm >= 1.0 ? 0.15 + 0.45 * t : 0.0;
  vAlpha = uRateScale * max(0.6 * nearSource, fromGrid) * (1.0 - age);
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_PointSize = uPointSize * (300.0 / max(-mv.z, 1.0));
  gl_Position = projectionMatrix * mv;
}
```
Particle fragment:
```glsl
uniform vec3 uColor;
varying float vAlpha;
void main() {
  vec2 c = gl_PointCoord - 0.5;
  float r2 = dot(c, c);
  if (r2 > 0.25 || vAlpha <= 0.001) discard;
  float soft = 1.0 - r2 * 4.0;
  gl_FragColor = vec4(uColor, vAlpha * soft * soft);
}
```
`uGridRect = (grid.x0_m, grid.y0_m, nx·dx_m, ny·dy_m)` (spec metres; the shader converts the scene `z` back to spec `y` with `−p.z`). `uPointSize` 1.6 (high), 2.0 (medium/low, fewer particles). Materials: `transparent`, `depthWrite: false`, `NormalBlending`; colours from CSS tokens (`--ch4-0..4`, `--plume-tint`) read once and converted with `THREE.Color` (sRGB → linear handled by `Color.setStyle`).

## Components
- **`usePlumeField(scenario)`** — returns a stable ref object `{ texA: DataTexture, texB: DataTexture, mix, windSpeed, towardX, towardZ, stability, sources }`; textures are created once (`RedFormat`, `UnsignedByteType`, `NearestFilter`, `needsUpdate = true`), and in `useFrame` (reading `useClockStore.getState().tSeconds`) the hook copies a frame's bytes into `texA.image.data` / `texB.image.data` **only when `a` or `b` changes**, then sets `needsUpdate`. No allocation in the frame loop.
- **`GroundHeatmap`** — `PlaneGeometry(nx·dx, ny·dy)` rotated −π/2 about X, centred at `specToScene([x0 + w/2, y0 + h/2, 0.05])`, `renderOrder = 1`, uniforms bound to the field ref, `raycast` no-op.
- **`PlumeParticles({ sourceIndex })`** — one `Points` per active source (0 or 1); `BufferGeometry` with `position` (zeros, required), `aSeed` (from `gaussianPairs`), `aOffset` (uniform `[0, 1)` from `mulberry32(11)`) created once per particle count; uniforms updated in `useFrame` by mutation: `uTime += delta` only while playing (clock store), `uSource` from the anchor node's world position (node index), `uToward`, `uSpeed`, `uSigmaSlope` (from the current key frame's stability), `uRateScale`. Source with an unknown anchor → not drawn + one `console.error`.
- **`PlumeLayer({ scenario })`** — mounts the field hook, the heat-map and `PlumeParticles` for `sources[0..1]` of the current frame.
- **`PlumeLegend`** (DOM, bottom-left of the station area) — title `Methane above background, ppm (model at 1.5 m)`; five swatches with labels `1`, `3`, `10`, `30`, `100+`; second line `Visualisation of the dispersion model. Methane is invisible.`; hidden when no scenario is loaded.
- **`SensorMarkers`** — for each methane sensor in `scenario.sensors`: post (cylinder r 0.05, h = `z_m`) + head box 0.25 m at the top, instanced (`InstancedMesh`, 2 meshes total); colour per instance: `--text-2` normal, `--alarm-med` when the sensor has a visible event in the last 30 min of simulation time, `--accent` when selected (instance colours updated only when the sample index or selection changes). A flat ring (torus, r 1.2) under each sensor with a recent event, one-shot scale animation 0.6 s (none with reduced motion). Each sensor has a hit proxy box (1 × 2.5 × 1 m) → `select(sensor_id)`.
- **`WindSock`** — at `MET-01` (`spec position`, mast pole r 0.05 from ground to `z`): sock = open cone (r 0.25 → 0.12, length 1.4 m, `paint_red`-like `#8c2a22` and `#e6e2da` bands via two meshes) pointing toward `windTowardScene`, pitch down `60° · (1 − min(speed, 7) / 7)`; updated per sample index (not per frame).
- **`FlareFlame`** — at node `FL-601.tip`: drei `Billboard` with a plane 1.2 × 2.4 m, `ShaderMaterial` (orange core `#ffb347`, `toneMapped = false`, colour × 4.0 so it passes the bloom threshold), flicker = `0.85 + 0.15·sin(uTime·13.0 + sin(uTime·7.0))` (`uTime` × 0.25 with reduced motion). The pilot is lit in every MVP scenario.
- **`CandidateHighlight({ candidates })`** — `candidates: { anchorId: string; label: string; probability: number }[]` (Phase 5 supplies them from the inversion tool result). Per candidate with a known anchor: sphere r 0.6 at the anchor, `meshStandardMaterial` colour `--candidate`, `emissive` same, `emissiveIntensity = 1 + 3·probability`, `toneMapped = false`; the top candidate (highest probability) also gets an `Html` label `<label> <probability as integer %>` (e.g. `VS-250 tip 87%`) — the label text comes from the props only.
- **`PostEffects`** — `EffectComposer multisampling={0}` with `Bloom luminanceThreshold={1} mipmapBlur intensity={0.6}` and `SMAA` on `high` and `medium`; not mounted on `low`.

## Tests (full code)
`plume/plumeMath.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import { alphaForPpm, decodeLogU8, keyframeAt, lerpAngleDeg, rateScale, windTowardScene } from "./plumeMath";

describe("plumeMath", () => {
  it("decodes the backend log_u8 encoding", () => {
    expect(decodeLogU8(0)).toBe(0);
    expect(decodeLogU8(1)).toBeCloseTo(0.1, 10);
    expect(decodeLogU8(255)).toBeCloseTo(1000, 6);
    expect(decodeLogU8(128)).toBeCloseTo(0.1 * 10 ** ((127 * 4) / 254), 9);
  });
  it("turns a meteorological 'from' direction into a scene 'toward' vector", () => {
    const [x1, z1] = windTowardScene(270);
    expect(x1).toBeCloseTo(1);
    expect(z1).toBeCloseTo(0);
    const [x2, z2] = windTowardScene(0);
    expect(x2).toBeCloseTo(0);
    expect(z2).toBeCloseTo(1);
  });
  it("interpolates angles along the short arc", () => {
    expect(lerpAngleDeg(350, 10, 0.5)).toBeCloseTo(0);
    expect(lerpAngleDeg(10, 350, 0.25)).toBeCloseTo(5);
  });
  it("finds the two key frames around a time", () => {
    expect(keyframeAt(130, 180)).toEqual({ a: 1, b: 2, mix: 10 / 120 });
    expect(keyframeAt(1e9, 180)).toEqual({ a: 179, b: 179, mix: 0 });
    expect(keyframeAt(5, 0)).toEqual({ a: 0, b: 0, mix: 0 });
  });
  it("maps concentration and rate to visibility", () => {
    expect(alphaForPpm(0.9)).toBe(0);
    expect(alphaForPpm(1)).toBeCloseTo(0.25);
    expect(alphaForPpm(100)).toBeCloseTo(0.75);
    expect(rateScale(1)).toBe(0.3);
    expect(rateScale(30)).toBe(1);
  });
});
```

`plume/plumeFrames.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import { makeReplay } from "@/shared/testing/replayFixture";

import { decodeKeyframes } from "./plumeFrames";

const grid = (fill: number) => btoa(String.fromCharCode(...new Uint8Array(1200).fill(fill)));

describe("decodeKeyframes", () => {
  it("decodes every frame once", () => {
    const s = makeReplay({
      keyframes: [
        { t_s: 0, wind_speed_m_s: 3, wind_from_deg: 250, stability: "D", sources: [], grid_b64: grid(0) },
        { t_s: 120, wind_speed_m_s: 4, wind_from_deg: 260, stability: "C", sources: [{ anchor_id: "VS-250.tip", rate_kg_h: 15 }], grid_b64: grid(9) },
      ],
    });
    const f = decodeKeyframes(s);
    expect(f.grids).toHaveLength(2);
    expect(f.grids[1]?.[0]).toBe(9);
    expect(f.sources[1]?.[0]?.anchor_id).toBe("VS-250.tip");
    expect(Array.from(f.times)).toEqual([0, 120]);
  });
  it("rejects a grid of the wrong size", () => {
    const s = makeReplay({
      keyframes: [{ t_s: 0, wind_speed_m_s: 3, wind_from_deg: 250, stability: "D", sources: [], grid_b64: btoa("abc") }],
    });
    expect(() => decodeKeyframes(s)).toThrow("plume grid has 3 bytes, expected 1200");
  });
});
```

`plume/PlumeLayer.test.tsx` (test-renderer): render `PlumeLayer` inside `NodeIndexContext` with a fake index containing `VS-250.tip`, scenario with 2 key frames (frame 1 has the source); `useClockStore` reset to 240 s, seek 130, playing; `advanceFrames(2, 1 / 60)`; assert: one `Points` object exists, the heat-map material's `uMix` uniform ≈ `10 / 120`, `uGridB` texture data byte 0 equals frame 1's byte 0, and `uTime` advanced by ≈ 2/60. Then pause and advance → `uTime` unchanged.

`overlays/SensorMarkers.test.tsx`: with the fixture plus 3 extra sensors (4 total), the post `InstancedMesh` has `count === 4`; clicking the proxy named `AT-101__hit` selects `AT-101`.

`overlays/CandidateHighlight.test.tsx`: two candidates (`VS-250.tip` p 0.87, `K-202.packing` p 0.10) → two spheres; the first sphere's `emissiveIntensity` ≈ 3.61 and the second ≈ 1.3; an unknown anchor id is skipped (no throw). (Pass `labels={false}` as in Task 8.)

## Steps
- [ ] Add deps (exact). Pure tests → FAIL → implement `plumeMath`, `plumeFrames`, `random`.
- [ ] Shaders/materials, field hook, heat-map, particles, layer; component tests → FAIL → implement → green.
- [ ] Sensors, windsock, flare, candidate highlight, post effects, legend.
- [ ] `npm run lint && npm run typecheck && npm run test && npm run build`.
- [ ] Browser, S1 at 120×: before 7200 s no plume; after the release starts the heat-map appears **downwind** of VS-250 matching the wind readout (check the compass); particles drift the same way; alarms fire on the sensors under the heat-map. S4: plume only during the blowdown window. S5: **no plume at all** (the drift is a sensor fault) — this is the honesty check; record it.
- [ ] Measure at `REVIEW_CAMERA`, S1 at +02:20, high: draw calls, triangles, fps (30 s) → work log; ≥ 58 fps; else reduce `plumeParticles` for the tier that fails and record.
- [ ] Screenshot `docs/evidence/2026-11-phase-4-plume-s1.png`; `check_slop.py`; `impeccable` critique of legend + labels; repo checks.
- [ ] **Docs.** FRONTEND.md → "Plume and effects": data path (key frames → textures), decode formula, threshold and ramp, particle model (visual spread table, grid gating, wall-clock motion), sensors/windsock/flare/candidates, post effects per tier, measurements. Work-log; `STATUS.md` (last 4.9, next 4.10).
- [ ] **Commit** `feat(3d): add plume heat-map, particles, sensors, windsock, flare and candidate highlight`.
