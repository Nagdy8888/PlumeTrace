# Phase 4 · Task 8 — R3F station view: node index, picking, selection, camera, quality tiers

**Skills:** `plan-execution`, `frontend-3d` (+ `references/performance-and-testing.md`), `frontend-structure`, `project-documentation`.
**Docs to check first (Context7):** R3F 9.8.2 (`Canvas` props `frameloop`, `dpr`, `shadows`; `useFrame`; `useThree`; `invalidate`; pointer events + `stopPropagation`), drei 10.7.9 (`useGLTF`, `CameraControls`, `PerformanceMonitor`, `Html`), @react-three/test-renderer 9.1.1 (`create`, `fireEvent`, `advanceFrames`), @react-three/eslint-plugin 0.1.2 (flat-config usage).

**Works on either approach:** the input is a `THREE.Object3D` root whose tree follows the contract
(tag-named groups, anchor-named children, `<tag>__<part>` separate nodes). In approach B it comes
from `useGLTF`; in fallback A from `SiteLayout`.

## Files (`app/frontend/src/features/station3d/` unless noted)
| Action | Path |
|---|---|
| Modify | `app/frontend/package.json` → dev `"@react-three/test-renderer": "9.1.1"`, `"@react-three/eslint-plugin": "0.1.2"`; `eslint.config.js` → enable the plugin's recommended rules for `src/features/station3d/**` |
| Create | `store.ts`, `store.test.ts` (quality tier + camera mode) |
| Create | `model/nodeIndex.ts`, `model/nodeIndex.test.ts`, `model/HitProxies.tsx`, `model/AnimatedParts.tsx`, `model/StationScene.tsx`, `model/StationScene.test.tsx` |
| Modify | `model/StationModel.tsx` (loads, prepares, passes the root to `StationScene`), `StationCanvas.tsx`, `StationView.tsx` |
| Create | `scene/CameraRig.tsx`, `interaction/useCameraFlyTo.ts`, `interaction/flyToTarget.ts`, `interaction/flyToTarget.test.ts`, `overlays/SelectionBox.tsx`, `overlays/TagLabel.tsx`, `overlays/QualityMenu.tsx` |
| Create | `scene/qualitySettings.ts` |
| Modify | `src/app/AppShell.tsx` (mount `StationView` in the station area, `ScenarioStatus` stays on top) |

## Interfaces
`scene/qualitySettings.ts`:
```ts
/** Rendering quality tiers (frontend-3d rule 6). */
export type QualityTier = "high" | "medium" | "low";

/** Per-tier canvas settings. Plume counts are used by Task 9. */
export const QUALITY: Record<QualityTier, { dpr: [number, number]; shadows: boolean; shadowMapSize: number; plumeParticles: number }> = {
  high: { dpr: [1, 1.5], shadows: true, shadowMapSize: 2048, plumeParticles: 40000 },
  medium: { dpr: [1, 1.25], shadows: true, shadowMapSize: 1024, plumeParticles: 20000 },
  low: { dpr: [1, 1], shadows: false, shadowMapSize: 512, plumeParticles: 10000 },
};
```

`store.ts` (Zustand):
- State: `override: QualityTier | "auto"` (initial from `localStorage["plumetrace.quality"]` when valid, else `"auto"`; storage errors are ignored), `autoTier: QualityTier` (initial `"high"`), `reducedMotion: boolean` (from `matchMedia("(prefers-reduced-motion: reduce)")`, updated on change).
- Derived hook `useQualityTier(): QualityTier` → `override === "auto" ? autoTier : override`.
- Actions: `decline()` (`high → medium → low`, stays at `low`), `setOverride(v)` (also writes localStorage), `setReducedMotion(b)`.

`model/nodeIndex.ts`:
```ts
import type { Object3D } from "three";

/** Lookup from contract names (tags, anchor ids, `<tag>__<part>`) to scene objects. */
export interface NodeIndex {
  get(name: string): Object3D | undefined;
  readonly equipmentTags: readonly string[];
  readonly missing: readonly string[];
}

/**
 * Index the station tree. Every equipment tag and anchor id of the spec must be present;
 * absent names are listed in `missing` (the view logs them once with console.error).
 *
 * @param root - Loaded or procedurally built station root.
 * @param spec - Facility spec (from `shared/facility/ks07.json`).
 * @returns The index.
 */
export function buildNodeIndex(root: Object3D, spec: FacilitySpec): NodeIndex;
```
(`FacilitySpec` from `@/shared/types/generated/contract`; first match wins when a name repeats.)

`interaction/flyToTarget.ts`:
- `export function flyToTarget(box: { min: Vec3; max: Vec3 }, cameraPos: Vec3): { position: Vec3; target: Vec3 }` — target = box centre; distance `d = max(12, 2.5 · largest box dimension)`; keep the camera's current horizontal direction from the target (azimuth), set elevation to 30°; position = target + d · (cos30°·horizontal unit + sin30°·up). If the camera is directly above (horizontal length < 1e-6), use the review camera's azimuth (south-west). `Vec3 = [number, number, number]`.
- `export function instrumentBox(position_m: Vec3): { min: Vec3; max: Vec3 }` — a 2 m cube centred on `specToScene(position_m)`.

**`model/StationModel.tsx`** — `useGLTF("/models/ks07.glb", false, true)`; once (`useMemo` on `scene`): every mesh `castShadow = receiveShadow = true` and `raycast = () => undefined` (no-op; only proxies are pickable); returns `<StationScene root={scene} spec={facility} />`.

**`model/StationScene.tsx`** — props `root`, `spec`; optional `labels` (default `true`); builds `buildNodeIndex` (memo), renders `<primitive object={root} dispose={null} />`, `<HitProxies index spec />`, `<AnimatedParts index />`, `<SelectionBox index spec />`, `<TagLabel index spec />` (only when `labels`). Exposes the index through a React context `NodeIndexContext` (exported from `model/nodeIndex.ts`) for Task 9.

**`model/HitProxies.tsx`** — for each equipment tag: compute the world `Box3` of the tag node once (memo), render one `<mesh>` with a unit `boxGeometry` scaled to the box size at its centre, material `meshBasicMaterial colorWrite={false} depthWrite={false}`, `name={\`${tag}__hit\`}`. Handlers: `onPointerOver` → `hover(tag)` + `document.body.style.cursor = "pointer"`; `onPointerOut` → `hover(null)` + cursor reset; `onClick` → `select(tag)`; every handler calls `e.stopPropagation()`. The geometry is shared (one module-level `BoxGeometry(1, 1, 1)`); the material is shared.

**`model/AnimatedParts.tsx`** — finds `E-231__fan_1` … `E-233__fan_2` via the index; in one `useFrame` rotates each about its local up axis by `delta · speed` (speed 2.0 rad/s, 0.5 when `reducedMotion`). No allocation; refs only.

**`overlays/SelectionBox.tsx`** — when a tag is selected (selection store, subscribed with a selector), draws `lineSegments` of the box edges (`EdgesGeometry` of the shared unit box, scaled) in `--accent` (read once from CSS), `depthTest = false`, `renderOrder = 10`. Hidden (`visible = false`) when nothing is selected — never unmounted per selection. Hover shows the same box in `--text-2` at 50 % opacity.

**`overlays/TagLabel.tsx`** — one drei `Html` label for the hovered tag and one for the selected tag (max two `Html` elements), positioned at the top centre of the box + 1 m; content `<span className="font-mono text-xs …">K-202</span> <span>Recip compressor</span>` (type label from a fixed map of the 15 `EquipmentType` values to English names, e.g. `recip_compressor → "Recip compressor"`, `fin_fan_cooler → "Fin-fan cooler"`, `teg_contactor → "TEG contactor"`), `pointer-events: none`, background `bg-surface-1/90`, border `border-border-2`. Instrument tags show their kind (`methane_point → "Methane sensor"`).

**`scene/CameraRig.tsx`** — drei `<CameraControls makeDefault minDistance={8} maxDistance={350} maxPolarAngle={(85 * Math.PI) / 180} />`; on mount `setLookAt(...REVIEW_CAMERA.position, ...REVIEW_CAMERA.target, false)`. Mounts `useCameraFlyTo`.

**`interaction/useCameraFlyTo.ts`** — subscribes to `selectedTag`; resolves a box (equipment: node `Box3`; instrument: `instrumentBox`; unknown: ignore); calls `controls.setLookAt(...position, ...target, !reducedMotion)` — reduced motion → instant jump, no flight. A `Reset view` action (`R` key, and a button in `QualityMenu`) returns to `REVIEW_CAMERA` the same way.

**`overlays/QualityMenu.tsx`** — DOM overlay (top-right of the station area, outside the canvas): native `<select aria-label="3D quality">` with `Auto`, `High`, `Medium`, `Low`, and a `Reset view` button. Text only, `text-xs`.

**`StationCanvas.tsx`** — `<Canvas frameloop={playing ? "always" : "demand"} dpr={QUALITY[tier].dpr} shadows={QUALITY[tier].shadows} gl={{ antialias: true, powerPreference: "high-performance" }} camera={{ fov: REVIEW_CAMERA.fov, near: 0.5, far: 2000, position: REVIEW_CAMERA.position }}>` → `<PerformanceMonitor onDecline={decline} flipflops={3} onFallback={() => setOverride("low")}>` → `Suspense` → environment, `Sun` (shadow map size from the tier), `StationModel`, `CameraRig`. `playing` comes from `useClockStore` with a selector. In dev, `?perf` mounts the perf overlay (Task 5).

**`StationView.tsx`** — lazy canvas + `QualityMenu`; logs `index.missing` once via `console.error("station model is missing nodes", missing)` (dev and prod).

## Tests (full code)
`model/nodeIndex.test.ts`:
```ts
import { Group, Object3D } from "three";
import { describe, expect, it } from "vitest";

import type { FacilitySpec } from "@/shared/types/generated/contract";

import { buildNodeIndex } from "./nodeIndex";

const spec = {
  equipment: [
    { tag: "K-202", anchors: [{ id: "K-202.packing" }, { id: "K-202.engine_exhaust" }] },
    { tag: "VS-250", anchors: [{ id: "VS-250.tip" }] },
  ],
} as unknown as FacilitySpec;

function named<T extends Object3D>(o: T, name: string): T {
  o.name = name;
  return o;
}

describe("buildNodeIndex", () => {
  it("finds tags and anchors and lists what is missing", () => {
    const root = new Group();
    const k = named(new Group(), "K-202");
    k.add(named(new Object3D(), "K-202.packing"));
    root.add(k, named(new Group(), "VS-250"));
    const index = buildNodeIndex(root, spec);
    expect(index.get("K-202")).toBe(k);
    expect(index.get("K-202.packing")?.parent).toBe(k);
    expect(index.equipmentTags).toEqual(["K-202", "VS-250"]);
    expect(index.missing).toEqual(["K-202.engine_exhaust", "VS-250.tip"]);
  });
});
```

`store.test.ts`:
```ts
import { beforeEach, describe, expect, it } from "vitest";

import { useStationStore } from "./store";

describe("station store", () => {
  beforeEach(() => useStationStore.setState(useStationStore.getInitialState()));
  it("declines one tier at a time and stops at low", () => {
    const s = useStationStore.getState();
    s.decline();
    expect(useStationStore.getState().autoTier).toBe("medium");
    s.decline();
    s.decline();
    expect(useStationStore.getState().autoTier).toBe("low");
  });
  it("persists a manual override", () => {
    useStationStore.getState().setOverride("low");
    expect(localStorage.getItem("plumetrace.quality")).toBe("low");
  });
});
```

`interaction/flyToTarget.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import { flyToTarget, instrumentBox } from "./flyToTarget";

describe("flyToTarget", () => {
  it("keeps the camera azimuth and looks down at 30 degrees from at least 12 m", () => {
    const { position, target } = flyToTarget({ min: [0, 0, 0], max: [2, 2, 2] }, [101, 50, 1]);
    expect(target).toEqual([1, 1, 1]);
    const [dx, dy, dz] = [position[0] - 1, position[1] - 1, position[2] - 1];
    expect(Math.hypot(dx, dy, dz)).toBeCloseTo(12);
    expect(Math.atan2(dy, Math.hypot(dx, dz))).toBeCloseTo(Math.PI / 6);
    expect(dz).toBeCloseTo(0);
    expect(dx).toBeGreaterThan(0);
  });
  it("centres a 2 m box on an instrument", () => {
    expect(instrumentBox([195, 75, 2])).toEqual({ min: [194, 1, -76], max: [196, 3, -74] });
  });
});
```

`model/StationScene.test.tsx`:
```tsx
import ReactThreeTestRenderer from "@react-three/test-renderer";
import { Group } from "three";
import { beforeEach, describe, expect, it } from "vitest";

import facility from "@/shared/facility/ks07.json";
import { useSelectionStore } from "@/shared/selection";
import type { FacilitySpec } from "@/shared/types/generated/contract";

import { StationScene } from "./StationScene";

function fakeRoot(): Group {
  const root = new Group();
  for (const e of facility.equipment) {
    const g = new Group();
    g.name = e.tag;
    g.position.set(e.position_m[0], e.position_m[2], -e.position_m[1]);
    root.add(g);
  }
  return root;
}

describe("StationScene", () => {
  beforeEach(() => useSelectionStore.setState(useSelectionStore.getInitialState()));
  it("creates one hit proxy per equipment item and selects on click", async () => {
    const r = await ReactThreeTestRenderer.create(
      <StationScene root={fakeRoot()} spec={facility as unknown as FacilitySpec} labels={false} />,
    );
    const proxies = r.scene.findAll((n) => n.props.name?.endsWith?.("__hit"));
    expect(proxies).toHaveLength(facility.equipment.length);
    const k202 = proxies.find((p) => p.props.name === "K-202__hit");
    expect(k202).toBeDefined();
    await r.fireEvent(k202!, "onClick");
    expect(useSelectionStore.getState().selectedTag).toBe("K-202");
  });
});
```
(`HitProxies` gives a node with an empty bounding box a 1 m box at the node's world position, so the fake root works. drei `Html` does not render in the test renderer, so `StationScene` takes `labels?: boolean` (default `true`) and this test passes `labels={false}`.)

## Steps
- [ ] Add dev deps (exact) and the ESLint plugin config; tests → FAIL → implement in this order: `qualitySettings`, `store`, `nodeIndex`, `flyToTarget`, `HitProxies`, `StationScene`, `SelectionBox`, `TagLabel`, `AnimatedParts`, `CameraRig` + `useCameraFlyTo`, `QualityMenu`, canvas/view wiring.
- [x] `npm run lint && npm run typecheck && npm run test && npm run build`.
- [x] Browser (Playwright CLI skill), 1920×1080, `npm run dev`: hover and click K-202 → label + box, camera flies; click an alarm in the list → camera flies to that sensor; `R` resets; with OS reduced motion on (Playwright `reducedMotion: "reduce"`), the camera jumps instead of flying; quality menu changes dpr/shadows (check `?perf`). Console shows no `station model is missing nodes`.
- [x] Record at `REVIEW_CAMERA`, quality high: `gl.info.render.calls`, `.triangles`, `.memory.textures`, fps (perf overlay, 30 s) → work log. Must stay ≤ 300 calls and ≥ 58 fps on the owner's integrated-graphics laptop; else follow the fix order in Task 7 and record.
- [x] Screenshot `docs/evidence/2026-11-phase-4-station.png`; `check_slop.py`; `impeccable` critique of the overlay chrome (labels, menu); repo checks.
- [x] **Docs.** FRONTEND.md → "3D station": object-tree contract, node index, picking (proxies only), selection/hover visuals, camera rules (limits, fly-to formula, reduced motion, reset), quality tiers table, measurements. Work-log; `STATUS.md` (last 4.8, next 4.9).
- [ ] **Commit** `feat(3d): add station view with picking, selection, camera and quality tiers`.
