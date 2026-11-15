# scripts/blender: the station generator (approach B)

Generates the 3D station from the facility spec with Blender Python (bpy), bakes ambient
occlusion and exports one glb. Nothing is modelled by hand: rerunning the script reproduces the
model (seeded randomness only). Status: Phase 4 Task 5 spike (K-202 with shelter, VS-250 and a
ground patch). Task 6 adds the other equipment types, Task 7 the full station.

## Versions

| Tool | Version |
|---|---|
| Blender | 4.5.16 LTS (blender.org; the build refuses any other 4.x or 5.x line) |
| glTF-Transform CLI | 4.5.1 (`npx --yes @gltf-transform/cli@4.5.1`) |
| Poly Haven assets | CC0, pinned in `polyhaven_manifest.json` (see [../../docs/reference/ASSETS.md](../../docs/reference/ASSETS.md)) |

Blender is not on PATH here; the path used is recorded in
[../../docs/LOCAL_DEVELOPMENT.md](../../docs/LOCAL_DEVELOPMENT.md).

## Commands (repo root)

```bash
cd app && uv run python ../scripts/fetch_polyhaven.py --record   # once; later without --record
cd ..
BLENDER=<path to blender.exe>
"$BLENDER" --background --factory-startup --python scripts/blender/build_station.py -- \
  --spec app/frontend/src/shared/facility/ks07.json --out build/ks07_raw.glb \
  --bake high --only K-202,VS-250         # --bake none|low|high (low: quick preview)
npx --yes @gltf-transform/cli@4.5.1 optimize build/ks07_raw.glb app/frontend/public/models/ks07.glb \
  --compress meshopt --texture-compress webp --texture-size 512 \
  --join false --flatten false --simplify false --palette false --prune false
cd app && uv run python ../scripts/check_glb.py --glb frontend/public/models/ks07.glb \
  --spec frontend/src/shared/facility/ks07.json --only K-202,VS-250 --max-bytes 2000000
```

The shipped spike `ks07.glb` (722,820 bytes) was built with exactly these commands. With
`--texture-size 1024` the same model is 2,598,024 bytes and fails the `--max-bytes 2000000` check, so
the single permitted retry at 512 is the command above (both sizes: `docs/evidence/2026-11-spike.md`).

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
| `layout.py` | `to_local` / `to_world` (spec position and rotation about z) |

Blender-only:

| Module | Does |
|---|---|
| `build_station.py` | entry: arguments after `--`, version check, build, assign, join, bake, export |
| `scene_setup.py` | `reset_scene`, `BuildContext` (root object per tag, part registry) |
| `parts/mesh_ops.py` | bmesh box, plane, cylinder, half cylinder, tube; bevel; box UV; shading |
| `parts/{skid,vessel,handrail,flange}.py` | parametric parts |
| `equipment/{compressor,shelter,vent_stack,ground}.py` | spike equipment; `equipment/__init__.py` holds `BUILDERS` (type to builder) |
| `materials.py` | Principled BSDF materials from the Poly Haven textures; one copy per equipment item |
| `bake.py` | `AO` UV layer (`uv.lightmap_pack`), Cycles AO bake, `glTF Material Output` occlusion |
| `export.py` | anchors, join each item into one node named by its tag, `export_scene.gltf` |

## Conventions

- Spec and Blender are Z-up (x east, y north). The glTF exporter's +Y-up conversion gives three.js
  `(x, z, -y)`; the frontend does the same in `scene/coords.ts`.
- Node names: equipment root = tag (`K-202`), anchors = `<tag>.<anchor>` (empties, children of the
  root), the ground patch = `ground`. UV set 0 `UVMap` (box projection), UV set 1 `AO`.
- Parts are built item-local and parented to the item's root; `join_equipment` runs before the
  bake so each item has one AO image (`<tag>_ao`, 512 px, or 1024 px with `--bake high`).
- Textures: `build/polyhaven/` (git-ignored). Only the HDRI is committed.
