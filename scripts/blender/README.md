# scripts/blender: the station generator (approach B)

Generates the 3D station from the facility spec with Blender Python (bpy), bakes ambient
occlusion and exports one glb. Nothing is modelled by hand: rerunning the script reproduces the
model (seeded randomness only). Status: Phase 4 Task 5 spike, Task 6 (a builder for each of the 15
equipment types, 24 items) and Task 7 (piping, pipe racks, site, full bake, one-command export and
budget check; the shipped `ks07.glb` is the full station). Deep references:
[../../docs/reference/BLENDER_EQUIPMENT.md](../../docs/reference/BLENDER_EQUIPMENT.md) (parts and
equipment) and [../../docs/reference/STATION_MODEL.md](../../docs/reference/STATION_MODEL.md)
(piping, site, bake, export, budgets).

## Versions

| Tool | Version |
|---|---|
| Blender | 4.5.16 LTS (blender.org; the build refuses any other 4.x or 5.x line) |
| glTF-Transform CLI | 4.5.1 (`npx --yes @gltf-transform/cli@4.5.1`) |
| Poly Haven assets | CC0, pinned in `polyhaven_manifest.json` (see [../../docs/reference/ASSETS.md](../../docs/reference/ASSETS.md)) |

Blender is not on PATH here; the path used is recorded in
[../../docs/LOCAL_DEVELOPMENT.md](../../docs/LOCAL_DEVELOPMENT.md).

## One command (repo root, Git Bash)

```bash
export BLENDER="C:/Users/Nagdy/Tools/blender-4.5.16/blender-4.5.16-windows-x64/blender.exe"
scripts/build_station.sh high     # or: low (quick preview bake)
```

`scripts/build_station.sh [low|high]` regenerates the contract JSON, builds the whole station
(no `--only`), optimises it with glTF-Transform (`--texture-size 512`, `--prune false`), writes
`build/ks07_inspect.txt` and runs `check_glb.py` with the budgets (15 MB, 1.5 M triangles, 300 draw
calls; it also requires every tag, anchor and the seven separate nodes). It exits non-zero on a
failure. Output and numbers: [../../docs/evidence/2026-11-ks07-glb.md](../../docs/evidence/2026-11-ks07-glb.md).

## Commands for a subset (repo root)

```bash
cd app && uv run python ../scripts/fetch_polyhaven.py --record   # once; later without --record
cd ..
BLENDER=<path to blender.exe>
"$BLENDER" --background --factory-startup --python scripts/blender/build_station.py -- \
  --spec app/frontend/src/shared/facility/ks07.json --out build/ks07_raw.glb \
  --bake high --only K-202,VS-250         # --bake none|low|high (low: quick preview)
  # --only builds the selected items and the ground only: no piping, racks, fence or bund
  # add --still build/stills/<type>.png for a 960 x 540 review render of the first --only tag
npx --yes @gltf-transform/cli@4.5.1 optimize build/ks07_raw.glb app/frontend/public/models/ks07.glb \
  --compress meshopt --texture-compress webp --texture-size 512 \
  --join false --flatten false --simplify false --palette false --prune false
cd app && uv run python ../scripts/check_glb.py --glb frontend/public/models/ks07.glb \
  --spec frontend/src/shared/facility/ks07.json --only K-202,VS-250 --max-bytes 2000000
```

The Task 5 spike `ks07.glb` (722,820 bytes) was built with exactly these commands. With
`--texture-size 1024` the same model is 2,598,024 bytes and fails the `--max-bytes 2000000` check, so
the single permitted retry at 512 is the command above (both sizes: `docs/evidence/2026-11-spike.md`).
The shipped glb is now the full station from `scripts/build_station.sh`. A `--only` build changes
the seeded paint factors and handwheel angles (they depend on build order).

`optimize` needs `--prune false`: version 4.5.1 prunes empty leaf nodes, which would delete the
anchor empties (`K-202.packing`, `VS-250.tip`). A glb built with `--prune true` fails
`check_glb.py` with `missing nodes`. There is no `--prune-leaves` flag in 4.5.1. The glb is loaded
without Draco (the Draco decoder would come from a CDN); meshopt is bundled with drei.

## Modules

Pure (no `bpy`, unit-tested from the uv environment in `app/backend/tests/blender/`):

| Module | Does |
|---|---|
| `spec_loader.py` | `load_spec`, `select_equipment` (`--only`), `anchors_of` |
| `naming.py` | node, part, material and AO-image names (names are contracts) |
| `uvmath.py` | `box_uv`: world-space box projection |
| `layout.py` | `to_local` / `to_world` (spec position and rotation about z), `ao_resolution` (AO image size by type and level; used by `bake.py`) |
| `piping_math.py` | `pipe_radius_m`, `fillet_polyline`, `support_points` (route geometry maths) |
| `fence_math.py` | `fence_post_xy`: post positions every 3 m on the four bounds, none outside the yard, gate gap left open |
| `anchors.py` | `anchor_local`: item-local position of a spec anchor |

Blender-only:

| Module | Does |
|---|---|
| `build_station.py` | entry: arguments after `--`, version check, build, assign, join, bake, export |
| `scene_setup.py` | `reset_scene`, `BuildContext` (root object per tag, part registry) |
| `parts/mesh_ops.py` | bmesh box, plane, cylinder, cone, torus, half cylinder, tube; bevel; box UV; shading |
| `parts/{solids,shapes}.py` | facet rule and bmesh cone; bevelled block, rod between two points, slab, tilt |
| `parts/{skid,vessel,handrail,flange,nozzle,valve,saddle,ladder,platform,separator}.py` | parametric parts |
| `equipment/<type>.py` (15 types) + `shelter.py` | one `build(item, ctx)` per type; `equipment/__init__.py` holds `BUILDERS` (type to builder) |
| `equipment/pipe_route.py` | `build(route, ctx)`: one `PIPE__<id>` tube per spec piping route, flanges, valves, supports |
| `equipment/pipe_rack.py` | `build_racks(ctx)`: the portal frames of the two headers, node `SITE__racks` |
| `equipment/site.py` | `build_ground(ctx, items, full)` (`SITE__ground`: yard, terrain, pads, road, bund) and `build_fence(ctx)` (`SITE__fence`) |
| `still.py` | optional review render (Cycles, 960 x 540); camera, sun and floor are removed again before the export |
| `materials.py` | Principled BSDF materials from the Poly Haven textures; one copy per equipment item |
| `bake.py` | `AO` UV layer (`uv.smart_project`), Cycles AO bake of every group but the piping, `glTF Material Output` occlusion |
| `export.py` | anchors, join each item into one node named by its tag, `export_scene.gltf` |

## Conventions

- Spec and Blender are Z-up (x east, y north). The glTF exporter's +Y-up conversion gives three.js
  `(x, z, -y)`; the frontend does the same in `scene/coords.ts`.
- Node names: equipment root = tag (`K-202`), anchors = `<tag>.<anchor>` (empties, children of the
  root), `SITE__ground`, `SITE__racks`, `SITE__fence`, piping `PIPE__<route id>` (`naming.py`). UV
  set 0 `UVMap` (box projection), UV set 1 `AO`.
- Separate nodes (`ctx.new_node`) are named `<tag>__<part>` and carry no baked AO: `E-231__fan_1`,
  `E-231__fan_2` (and `E-232`, `E-233`; origin at the hub, spin about local Y in three.js) and
  `FL-601__tip` (origin at z 28.5). Since Task 7 each has its own baked AO image.
- Parts are built item-local and parented to the item's root; `join_equipment` runs before the
  bake so each item has one AO image (`<tag>_ao`; size from `layout.ao_resolution`: 256 px on
  `low`; on `high` 1024 px for the compressors and `SITE__ground`, else 512 px).
- Textures: `build/polyhaven/` (git-ignored). Only the HDRI is committed.

## Equipment types (Task 6)

Item-local frame: `x` along the long axis, `y` across, `z` up. An anchor is always at the spec
position; the geometry named below touches it. Parts are in `parts/`, one builder per type in
`equipment/`. Facets: 32 from radius 0.3 m, 16 from 0.1 m, 8 below.

| Type (tags) | Parts | Anchor (geometry) | Separate nodes |
|---|---|---|---|
| `pig_trap` (PIG-101, PIG-702) | pad, barrel D 0.6, reducer, line stub, door disc, 2 saddles, kicker valve | `door` (door disc centre; door end = sign of its local x) | none |
| `filter_separator` (V-100) | skirt, vessel, PSV, 2 nozzles, gauge, ring platform, caged ladder | `psv` (PSV top, z 6.0) | none |
| `scrubber` (V-211..213) | as V-100, no platform, uncaged ladder with brackets | `psv` (z 5.0) | none |
| `recip_compressor` (K-201..203) | Task 5 spike builder | `packing`, `engine_exhaust` | none |
| `fin_fan_cooler` (E-231..233) | 4 legs, plenum, bundle, headers, rings, motors, walkway | none | `<tag>__fan_1`, `<tag>__fan_2` |
| `vent_stack` (VS-250) | Task 5 spike builder | `tip` | none |
| `teg_contactor` (T-301) | skirt, vessel, 8 banding rings, 2 platforms, caged ladder, 2 nozzles | none | none |
| `teg_regenerator` (R-302) | reboiler on 2 saddles, firebox, burner stack, still column, surge drum | `still_vent` (still top, z 8.0) | none |
| `fuel_gas_skid` (FG-501) | skid, 2 filters, run with 4 valves, heater | `skid` (raised run section, z 1.5) | none |
| `storage_tank` (TK-401, TK-402) | shell, cone roof, hatch and lid, 45 degree stair, roof platform, nozzle | `thief_hatch` (lid top, z 7.0) | none |
| `vru` (VRU-410) | skid, compressor box, motor, scrubber, panel | `skid` (discharge spool top, z 1.5) | none |
| `knockout_drum` (V-602) | vessel, 2 saddles, PSV body and outlet, drain nozzle | `psv` (outlet top, z 4.0) | none |
| `flare_stack` (FL-601) | base plate, 3 sections, 6 aviation bands, 2 platforms, caged ladder, pilot line | `tip` (shield ring top centre, z 30.0) | `FL-601__tip` |
| `meter_run` (M-701) | tube, bypass, meter box, 4 valves, 5 supports | `meter` (meter box centre) | none |
| `building` (CR-901, MCC-902) | panel box, parapet, door, HVAC; windows (CR-901) or louvres (MCC-902) | none | none |

Check one type (see the page for expected output): build with `--bake none --only <tags>`, then
`check_glb.py --only <tags>`; `--still` gives the review picture (stills of the 13 new types are
in [../../docs/evidence/2026-11-equipment/](../../docs/evidence/2026-11-equipment/)).
