# Phase 4 · Task 5b — Fallback approach A: procedural R3F station (ONLY if the owner said no-go)

**Run this task only when `STATUS.md` records the owner's spike answer as no-go.** Then Tasks 6
and 7 are skipped and Task 8 continues on top of this one.

**Skills:** `plan-execution`, `frontend-3d` (+ `references/procedural-equipment.md`, `performance-and-testing.md`), `project-documentation`.
**Docs to check first (Context7):** three 0.187.0 (`LatheGeometry`, `InstancedMesh`, `BufferGeometryUtils.mergeGeometries`), R3F 9.8.2, drei 10.7.9 (`Instances`, `Merged`, `useTexture`), @react-three/postprocessing 3.2.2 (`EffectComposer`, `N8AO`).

## The contract that must not change
Task 8 onward reads the station only through `nodeIndex` (tag → `Object3D`, anchor id → `Object3D`).
Approach A must produce **the same object tree** as the glb: one `Group` named exactly the tag per
equipment item, and one child `Object3D` named exactly the anchor id at each anchor. Then Tasks
8–11 work unchanged. Coordinates: `specToScene` from Task 5.

## Files (`app/frontend/src/features/station3d/`)
| Action | Path |
|---|---|
| Delete | `public/models/ks07.glb` (spike output) and its `useGLTF` call; `StationModel.tsx` becomes the procedural root |
| Create | `procedural/SiteLayout.tsx` (maps spec items through the registry), `procedural/equipmentRegistry.ts`, `procedural/AnchorNodes.tsx` |
| Create | `procedural/parts/Vessel.tsx`, `Skid.tsx`, `Handrail.tsx` (instanced posts), `Flange.tsx` (instanced), `Pipe.tsx` (tube along waypoints, elbow radius 1.5·D) |
| Create | `procedural/equipment/` — one component per `EquipmentType` value (15 files: `PigTrap.tsx`, `FilterSeparator.tsx`, `Scrubber.tsx`, `RecipCompressor.tsx`, `FinFanCooler.tsx`, `VentStack.tsx`, `TegContactor.tsx`, `TegRegenerator.tsx`, `FuelGasSkid.tsx`, `StorageTank.tsx`, `Vru.tsx`, `KnockoutDrum.tsx`, `FlareStack.tsx`, `MeterRun.tsx`, `Building.tsx`) plus `Shelter.tsx` |
| Create | `procedural/materials.ts` (one material instance per key, module scope, same values as the `materials.py` table in Task 5), `procedural/textures.ts` (drei `useTexture` of the Poly Haven 1k JPG maps, copied by `scripts/fetch_polyhaven.py --copy-to-public` from `build/polyhaven/` to `app/frontend/public/textures/<id>/` — add that flag in this task; committed, ≤ 15 MB total, listed in `docs/reference/ASSETS.md`) |
| Create | `scene/PostEffects.tsx` (`N8AO` on the "high" tier only) |
| Create (tests) | `procedural/SiteLayout.test.tsx` (test-renderer), `procedural/equipmentRegistry.test.ts` |

## Rules
- Geometry for every type: the part tables in `task-06-bpy-equipment.md` (same parts, same dimensions, same anchors). Build them in R3F instead of bpy.
- Static parts of one equipment item are merged into one geometry per material (`mergeGeometries`) in `useMemo`; flanges, handrail posts and grating panels are `InstancedMesh` across the whole site.
- Fan blades (`E-23x__fan_n`) and the flare tip (`FL-601__tip`) stay separate named objects, exactly as in the glb naming (`<tag>__<part>`).
- Unknown equipment type → a `Group` named the tag with a 1 m wireframe box and `console.warn("no component for type …")`; never crash.
- Budgets are those of `frontend-3d` (≤ 300 draw calls, ≤ 1.5 M triangles at "high").

## Tests (full code)
`procedural/equipmentRegistry.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import facility from "@/shared/facility/ks07.json";

import { EQUIPMENT_COMPONENTS } from "./equipmentRegistry";

describe("equipmentRegistry", () => {
  it("has a component for every equipment type in the spec", () => {
    const types = new Set(facility.equipment.map((e) => e.type));
    for (const t of types) expect(EQUIPMENT_COMPONENTS[t as keyof typeof EQUIPMENT_COMPONENTS]).toBeDefined();
  });
});
```

`procedural/SiteLayout.test.tsx`:
```tsx
import ReactThreeTestRenderer from "@react-three/test-renderer";
import { describe, expect, it } from "vitest";

import facility from "@/shared/facility/ks07.json";

import { SiteLayout } from "./SiteLayout";

describe("SiteLayout", () => {
  it("creates one named group per tag and one node per anchor", async () => {
    const r = await ReactThreeTestRenderer.create(<SiteLayout spec={facility} quality="low" />);
    const names = new Set<string>();
    r.scene.instance.traverse((o) => names.add(o.name));
    for (const e of facility.equipment) {
      expect(names.has(e.tag)).toBe(true);
      for (const a of e.anchors ?? []) expect(names.has(a.id)).toBe(true);
    }
  });
});
```
(`@react-three/test-renderer` 9.1.1 is added as a dev dependency in this task; if `resolveJsonModule` is not on in `tsconfig.json`, add `"resolveJsonModule": true`.)

## Steps
- [ ] Confirm the no-go is recorded in STATUS.md (else STOP).
- [ ] Tests → FAIL → implement parts, then equipment types in this order: compressor + shelter, vent stack, scrubber, separator, fin-fan, TEG pair, tanks + VRU, KO drum + flare, meter run, pig traps, fuel gas skid, buildings, piping.
- [ ] Screenshot at `REVIEW_CAMERA` → `docs/evidence/2026-11-fallback-review.png`; measure fps and draw calls like the spike; record in the work log.
- [ ] Checks: lint, typecheck, test, build; `check_slop.py`; repo checks.
- [ ] **Docs.** FRONTEND.md → "3D station" states approach A, the object-tree contract, the folder layout. Work-log; `STATUS.md` (last 4.5b, next 4.8).
- [ ] **Commit** `feat(3d): build the station procedurally in R3F (fallback A)`.
