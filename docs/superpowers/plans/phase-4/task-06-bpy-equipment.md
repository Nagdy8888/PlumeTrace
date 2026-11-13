# Phase 4 · Task 6 — bpy parts library and every equipment type

**Run only after the owner's spike answer is "go" (recorded in STATUS.md).**
**Skills:** `plan-execution`, `frontend-3d` (+ `references/blender-pipeline.md`, `procedural-equipment.md`), `project-documentation`.
**Docs to check first:** Blender 4.5 Python API (`bmesh.ops.spin`, `bmesh.ops.create_circle`, `bmesh.ops.create_cone`, `bmesh.ops.translate`, `bmesh.ops.rotate`, `Object.parent`, `bpy.ops.object.join`).

**Goal:** a builder for each of the 15 `EquipmentType` values plus the shelter, built from shared
parts, with every spec anchor placed exactly. Task 7 adds piping, ground, bake and the full export.

## Conventions (apply to every builder)
- Local frame per item: `x` along the item's long axis, `y` across, `z` up, origin at `position_m` on the ground; `rotation_deg` rotates about z (`layout.to_world`). `L, W, H = size_m`.
- Every anchor empty is placed at the **spec** world position (never computed from geometry); geometry is placed so that the part named in the table touches the anchor.
- Segments: 32 for cylinders with radius ≥ 0.3 m, 16 for 0.1–0.3 m, 8 below 0.1 m. Bevel 0.02 m on boxes ≥ 1 m, none below.
- After building, all static mesh parts of one item are joined into one object named the tag; parts listed as **separate node** keep `naming.part_name(tag, part)` and are parented to the tag object with their origin at the stated pivot.
- Materials by key (Task 5 table plus the additions below). A builder never creates materials; it asks `materials.get(key)`.
- Builders are pure functions of `(item, ctx)`; seeded variation only from `ctx.rng` (used for: valve handwheel angles, ±2 % paint value jitter per item).

## Material additions (`materials.py`)
| key | Base colour (linear) | Roughness | Metallic | Textures |
|---|---|---|---|---|
| `paint_red` (aviation band) | (0.50, 0.05, 0.04) | 0.5 | 0.2 | `metal_plate` normal |
| `paint_white` | (0.80, 0.80, 0.78) | 0.5 | 0.2 | `metal_plate` normal |
| `building_panel` | (0.62, 0.62, 0.58) | 0.7 | 0.1 | `concrete_floor_02` normal (strength 0.3), tile 3 m |
| `glass` | (0.05, 0.07, 0.08) | 0.1 | 0.0 | none |
| `grating` | `metal_grate_rusty` diffuse | its roughness | 0.7 | its normal, tile 1 m |
| `pipe_gas` | (0.60, 0.58, 0.40) | 0.55 | 0.3 | `metal_plate` normal |

## Parts library (`scripts/blender/parts/`, each ≤ 300 lines, Google docstrings)
| Module | Function | Builds |
|---|---|---|
| `vessel.py` | `vessel(name, diameter_m, shell_length_m, axis: Literal["X", "Z"], location, heads="2:1")` | shell + two 2:1 elliptical heads (head depth = D/4) made with `bmesh.ops.spin` of a profile; total length = shell + D/2 |
| `nozzle.py` | `nozzle(name, radius_m, length_m, start, direction)` | short pipe + flange at the outer end |
| `skid.py` | `skid(name, length_m, width_m, height_m)` | two longitudinal W-beams + cross-beams every ≤ 2.5 m |
| `platform.py` | `platform(name, outline: list[(x, y)], z_m)` | 0.05 m grating plate (material `grating`) + toe plate + handrail along the open edges |
| `ladder.py` | `ladder(name, base, top_z, facing_deg, caged: bool)` | 2 rails (0.06 × 0.06 m) 0.45 m apart, rungs r 0.012 every 0.3 m; caged → hoops (torus r 0.35) every 0.9 m from 2.2 m above base |
| `handrail.py` | `handrail(name, points: list[(x, y, z)])` | posts every ≤ 1.5 m (r 0.025), top rail 1.1 m, knee rail 0.55 m, material `safety_yellow` |
| `flange.py` | `flange(name, pipe_radius_m, location, axis)` | disc r = pipe r + 0.06, thickness 0.04 |
| `valve.py` | `valve(name, pipe_radius_m, location, axis)` | body box (2.5 r × 2 r × 2 r) + stem + handwheel (torus r = 2 r) |
| `saddle.py` | `saddle(name, vessel_diameter_m, x_m)` | box saddle 0.3 × 0.8 D, height up to the vessel's underside |
| `mesh_ops.py` | from Task 5, plus `cone(name, r_bottom, r_top, depth, location)` and `torus(name, major_r, minor_r, location, axis)` | primitives |

## Equipment builders (`scripts/blender/equipment/`, one module per type; registry in `__init__.py`)
`BUILDERS: dict[str, Callable[[dict, BuildContext], Object]]` keyed by the `EquipmentType` value. Missing type → `sys.exit("no builder for type …")`.

**`pig_trap.py` (PIG-101, PIG-702; 6 × 1.2 × 1.5)** — door end = the end whose sign matches the door anchor's local x.
barrel: horizontal vessel shell (no heads) D 0.6, length L − 1.2, centre z 1.0 · reducer: cone D 0.6 → 0.4, 0.4 m long at the non-door end · line pipe stub D 0.4, 0.8 m · **closure door**: disc D 0.85 × 0.15 at the door end, centred on the anchor · 2 saddles at ±L/4 · kicker valve on top at 1/3 L · pad (concrete) (L + 1) × (W + 1) × 0.2.

**`filter_separator.py` (V-100; 2 × 2 × 6)** — skirt D 2.0, h 0.8 · vertical vessel D 2.0, shell H − 0.8 − 1.0, heads 0.5 each (top of top head = H − 0.4) · **PSV** cylinder r 0.1, from the top head to z H (anchor) · inlet nozzle r 0.3 at z 2.2 facing −x, outlet at z 4.2 facing +x · top platform: ring outline (16-gon, r D/2 + 0.9) at z H − 0.6 · caged ladder from z 0 to the platform on the −y side · level gauge (cylinder r 0.04, z 1.5–3.5) at +y, D/2 + 0.15.

**`scrubber.py` (V-211..213; 1.5 × 1.5 × 5)** — as filter separator without the platform; uncaged ladder to z H − 0.6; level gauge at +y.

**`compressor.py` (K-201..203)** — exactly the Task 5 table (already built).

**`shelter.py`** — exactly the Task 5 description.

**`fin_fan.py` (E-231..233; 8 × 4 × 5)** — 4 legs (boxes 0.25 × 0.25) at the corners, z 0–3.5 · plenum box L × W × 0.8 at z 3.5–4.3 (`paint_grey`) · tube bundle box L × W × 0.4 at z 4.3–4.7 (`paint_grey`) · inlet/outlet headers boxes 0.4 × W × 0.6 at x = ±(L/2 − 0.2), z 4.3–4.9 · 2 fan rings (torus major r 1.6, minor r 0.06) at x = ±L/4, z 3.4 · **separate nodes** `<tag>__fan_1` (x −L/4) and `<tag>__fan_2` (x +L/4), pivot at the hub, each: hub cylinder r 0.2 h 0.25 + 4 blades (box 1.45 × 0.28 × 0.03, pitched 12° about their long axis) · motor box 0.5 × 0.5 × 0.6 under each hub (z 2.6–3.2) · walkway grating along +y edge at z 4.7 with handrail.

**`vent_stack.py` (VS-250)** — exactly Task 5.

**`teg_contactor.py` (T-301; 1.5 × 1.5 × 15)** — skirt D 1.5, h 1.5 · vertical vessel D 1.5 from z 1.5 to H (heads included) · tray banding: flange rings (r D/2 + 0.03, thickness 0.05) every 1.5 m from z 3 · platforms (ring, r D/2 + 0.9) at z 7.0 and 13.5 · caged ladder z 0 → 13.5 on −y · inlet nozzle r 0.2 at z 2.5 (−x), outlet at z 14 (+x).

**`teg_regenerator.py` (R-302; 4 × 2 × 8)** — reboiler: horizontal vessel D 1.4, total length L, centre z 1.3, on 2 saddles · firebox box 1.2 × 1.2 × 1.2 at the −x end on the ground · burner stack cylinder r 0.15 from the firebox top to z 5.0 at x −L/2 + 0.4 · **still column** cylinder r 0.2 from the reboiler top (z 2.0) to z H at local (0, 0) — its top is the `R-302.still_vent` anchor · surge drum horizontal vessel D 0.8 length 2.0 at y +1.2, z 0.8.

**`fuel_gas_skid.py` (FG-501; 4 × 3 × 2)** — skid L × W × 0.25 · 2 vertical filter vessels D 0.4, shell 0.9, at x −1.2, y ±0.6 · regulator run: pipe r 0.05 along x at z 1.0, y 0, from x −1.8 to +1.8, with 4 valves at x −1.0, −0.3, +0.3, +1.0 · line heater box 1.0 × 0.8 × 1.0 at x +1.3, y +0.9 · the `FG-501.skid` anchor sits on the regulator run (local (0, 0, 1.5) — raise the run's centre pipe section by a vertical spool to z 1.5 between the two middle valves).

**`storage_tank.py` (TK-401, TK-402; 6 × 6 × 7)** — shell cylinder D 6, h H − 0.5 · cone roof from r 3.05 to the apex at z H · **thief hatch** box 0.4 × 0.4 × 0.15 + lid (0.45 × 0.45 × 0.03, tilted 5°) at the apex; the anchor is at the hatch top · straight stair: stringers + treads (0.25 m) rising 45° along the shell on the −y side to a 1.0 × 1.5 m roof platform at the edge, handrail on both · nozzle r 0.15 at z 0.5 (−x).

**`vru.py` (VRU-410; 4 × 3 × 2.5)** — skid · screw compressor box 1.6 × 1.0 × 1.0 at x −0.5, z 0.25–1.25 · motor cylinder r 0.35, length 1.0 along x at x +0.9 · suction scrubber vertical vessel D 0.6, shell 1.4, at x −1.5, y +1.0 · control panel box 0.8 × 0.3 × 1.6 at y −1.3 · the `VRU-410.skid` anchor on top of the compressor box (add a 0.25 m discharge spool so geometry reaches z 1.5).

**`knockout_drum.py` (V-602; 6 × 2 × 2.5)** — horizontal vessel D 2.0, total length L, centre z 1.25, 2 saddles at ±L/4 · **PSV** body cylinder r 0.12, h 0.5 on top at local (0, 0) from z 2.25, outlet pipe r 0.08 rising to z 4.0 (anchor) · drain nozzle r 0.1 under the −x end.

**`flare_stack.py` (FL-601; 1 × 1 × 30)** — base plate 2 × 2 × 0.1 · stack sections: r 0.5 z 0.1–10, r 0.4 z 10–20, r 0.3 z 20–28.5 (cone transitions 0.5 m) · aviation bands: the top 9 m in alternating 1.5 m `paint_red` / `paint_white` sections · platforms (ring r 1.4) at z 15 and 28 · caged ladder 0 → 28 on −y · pilot gas line pipe r 0.025 up the +y side · **separate node** `FL-601__tip`, pivot at z 28.5: tip cylinder r 0.35, z 28.5–29.8 + wind shield ring (cylinder r 0.45, z 29.6–30.0, open top) — its top centre is the `FL-601.tip` anchor.

**`meter_run.py` (M-701; 10 × 2 × 1.5)** — meter tube pipe r 0.2 along x at z 1.0, y 0 · ultrasonic meter body box 0.6 × 0.5 × 0.6 centred at local (0, 0, 1.0) (= the `M-701.meter` anchor) · bypass pipe r 0.12 at y +0.6 · 4 valves (2 per line) at x ±3.5 · supports (box 0.2 × 1.6 × 0.8) every 2 m.

**`building.py` (CR-901, MCC-902)** — box L × W × H (`building_panel`) with a 0.3 m parapet · door inset (box 1.0 × 0.05 × 2.1, `paint_dark`) centred on the −y wall · CR-901 only: windows (box 1.2 × 0.05 × 1.0, `glass`) every 2.5 m along −y at z 1.0–2.0, skipping the door · roof HVAC box 1.5 × 1.0 × 0.8 · MCC-902: louvre panels (3 boxes 1.0 × 0.05 × 0.6) on +x.

## Pure helper addition (tested)
`layout.py` → `def ao_resolution(equipment_type: str, level: str) -> int`: `level == "low"` → 256; `level == "high"` → 1024 for `recip_compressor` and for the ground (`"ground"`), 512 for everything else. Any other level → `ValueError`. (Keeps total GPU texture memory under the 128 MB budget: see Task 7.)

Test (`app/backend/tests/blender/test_layout.py`, add):
```python
def test_ao_resolution_budget() -> None:
    """Large items get 1024 px AO at high quality, the rest 512 px; low is always 256 px."""
    mod = _load("layout")
    assert mod.ao_resolution("recip_compressor", "high") == 1024
    assert mod.ao_resolution("ground", "high") == 1024
    assert mod.ao_resolution("storage_tank", "high") == 512
    assert mod.ao_resolution("flare_stack", "low") == 256
    with pytest.raises(ValueError):
        mod.ao_resolution("vru", "ultra")
```
(Add `import pytest` at the top of the file if it is not there.)

## Verification per type
For each type, after writing its builder, run (fast, no bake):
```bash
blender --background --factory-startup --python scripts/blender/build_station.py -- \
  --spec app/frontend/src/shared/facility/ks07.json --out build/type_check.glb --bake none --only <TAGS>
cd app && uv run python ../scripts/check_glb.py --glb ../build/type_check.glb \
  --spec frontend/src/shared/facility/ks07.json --only <TAGS>
```
`<TAGS>` = every tag of that type. `check_glb.py` must print `glb OK`. Then render a still for review:
add `--still build/stills/<type>.png` to `build_station.py` (Cycles, 32 samples, 1280×720, camera
placed 2.5 × the item's largest dimension away at 30° elevation from the south-west, sun at 250° /
18°). Look at each still; fix anything floating, intersecting or missing before moving on.

## Steps
- [ ] Confirm "go" in STATUS.md (else STOP).
- [ ] `ao_resolution` test → FAIL → implement → green.
- [ ] Parts library, then builders in this order: scrubber, filter separator, knockout drum, pig trap, fin-fan, TEG contactor, TEG regenerator, tanks, VRU, fuel gas skid, meter run, flare stack, buildings. Verify each type (above).
- [ ] Full no-bake build of all tags (`--bake none`, no `--only`) → `check_glb.py` (no `--only`) prints `glb OK`.
- [ ] Copy the 13 stills into `docs/evidence/2026-11-equipment/` (PNG, ≤ 400 KB each — reduce to 960×540 if larger).
- [ ] Ruff on `scripts/`; pytest; repo checks (each module ≤ 300 lines, function ≤ 50 lines).
- [ ] **Docs.** `scripts/blender/README.md` → one section per equipment type (parts, anchors, separate nodes); FRONTEND.md → separate-node naming (`<tag>__fan_n`, `FL-601__tip`). Work-log; `STATUS.md` (last 4.6, next 4.7).
- [ ] **Commit** `feat(3d): add bpy parts library and builders for every equipment type`.
