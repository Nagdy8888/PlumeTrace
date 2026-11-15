# Phase 4 · Task 5 — Blender spike: K-202 with shelter + VS-250 through the full chain → OWNER GATE

**Skills:** `plan-execution`, `frontend-3d` (+ `references/blender-pipeline.md`, `procedural-equipment.md`, `performance-and-testing.md`), `project-documentation`.
**Docs to check first:** Blender **4.5** Python API (docs.blender.org/api/4.5: `bpy.ops.export_scene.gltf`, `bpy.ops.object.bake`, `bpy.ops.uv.lightmap_pack`, `bmesh.ops.create_cube`, `bmesh.ops.create_cone`, `bmesh.ops.bevel`), the Blender 4.5 manual page "glTF 2.0" → "Occlusion" (custom node group), glTF-Transform 4.5.1 CLI `optimize` / `inspect`, drei 10.7.9 `useGLTF` + `Environment`, R3F 9.8.2 `Canvas`. If any parameter named below does not exist in those docs, **STOP and ask** — do not substitute.

**Why a spike:** approach B is only worth it if a generated, baked model looks clearly better than
procedural R3F, holds 60 fps and stays small. Two days, one skid, then the owner decides.

## Prerequisites (STOP if missing)
- Blender **4.5.16 LTS** installed by the owner from blender.org; `blender --version` prints a first line starting `Blender 4.5.16`. If `blender` is not on PATH, the owner gives the full path; record it in `docs/LOCAL_DEVELOPMENT.md` (path only).
- **Download permission:** before running the asset download, ask the owner in chat, listing: source `https://api.polyhaven.com` / `dl.polyhaven.org` (CC0), the files below and the approximate total (≈ 12 MB for the five texture sets at 1k + 1.2 MB HDRI). Wait for a clear yes.

## Pinned assets (Poly Haven, CC0 — ids verified 2026-11-13)
| Use | Asset id | Maps (1k JPG) | Where |
|---|---|---|---|
| painted steel (normal + roughness only; colour comes from the paint value) | `metal_plate` | `nor_gl`, `Rough` | `build/polyhaven/` |
| concrete pads | `concrete_floor_02` | `Diffuse`, `nor_gl`, `Rough` | `build/polyhaven/` |
| yard ground | `gravel_floor_02` | `Diffuse`, `nor_gl`, `Rough` | `build/polyhaven/` |
| shelter roof / cladding | `corrugated_iron_02` | `Diffuse`, `nor_gl`, `Rough` | `build/polyhaven/` |
| grating (Task 6) | `metal_grate_rusty` | `Diffuse`, `nor_gl`, `Rough` | `build/polyhaven/` |
| sky / image lighting (runtime) | `industrial_sunset_puresky` | HDRI 1k `.hdr` | `app/frontend/public/textures/env/industrial_sunset_puresky_1k.hdr` (committed) |

## Files
| Action | Path |
|---|---|
| Modify | `.gitignore` → nothing new (`build/` is already ignored); `app/frontend/package.json` (deps below) |
| Create | `scripts/fetch_polyhaven.py`, `scripts/blender/polyhaven_manifest.json`, `scripts/check_glb.py` |
| Create (pure, no bpy) | `scripts/blender/spec_loader.py`, `scripts/blender/naming.py`, `scripts/blender/uvmath.py`, `scripts/blender/layout.py` |
| Create (bpy) | `scripts/blender/build_station.py`, `scripts/blender/scene_setup.py`, `scripts/blender/parts/__init__.py`, `parts/mesh_ops.py`, `parts/vessel.py`, `parts/skid.py`, `parts/handrail.py`, `parts/flange.py`, `scripts/blender/equipment/__init__.py` (registry), `equipment/compressor.py`, `equipment/shelter.py`, `equipment/vent_stack.py`, `equipment/ground.py`, `scripts/blender/materials.py`, `scripts/blender/bake.py`, `scripts/blender/export.py`, `scripts/blender/README.md` |
| Create (tests) | `app/backend/tests/blender/test_spec_loader.py`, `test_uvmath.py`, `test_layout.py`, `app/backend/tests/test_check_glb.py` |
| Create (frontend) | `src/features/station3d/index.ts`, `StationView.tsx`, `StationCanvas.tsx`, `scene/coords.ts`, `scene/coords.test.ts`, `scene/reviewCamera.ts`, `scene/EnvironmentMap.tsx`, `scene/Sun.tsx`, `model/StationModel.tsx`, `dev/PerfOverlay.tsx` |
| Generated | `app/frontend/public/models/ks07.glb` (spike content: K-202 + VS-250 + ground patch; Task 7 regenerates it with the full station), `docs/evidence/2026-11-spike-*.png`, `docs/evidence/2026-11-spike.md` |

Frontend dependencies (exact): `"three": "0.187.0"`, `"@react-three/fiber": "9.8.2"`, `"@react-three/drei": "10.7.9"`; dev: `"@types/three": "0.187.0"`, `"r3f-perf": "7.2.3"`.

## Pure helpers (full interfaces; Google docstrings; no `bpy` import; stdlib only)
`scripts/blender/spec_loader.py`:
- `def load_spec(path: Path) -> dict[str, Any]` — `json.loads(path.read_text(encoding="utf-8"))`; raises `ValueError("not a facility spec: missing equipment")` if `"equipment"` is absent.
- `def select_equipment(spec: dict[str, Any], only: frozenset[str] | None) -> list[dict[str, Any]]` — equipment in spec order; with `only`, the listed tags; an unknown tag in `only` → `ValueError(f"unknown tag {tag}")`.
- `def anchors_of(item: dict[str, Any]) -> list[tuple[str, tuple[float, float, float]]]` — `(anchor id, position_m)` pairs.

`scripts/blender/naming.py`:
- `def node_name(tag: str) -> str` → `tag` (equipment root node name is exactly the tag).
- `def part_name(tag: str, part: str) -> str` → `f"{tag}__{part}"` (double underscore; parts that stay separate nodes, e.g. `E-231__fan_1`).
- `def material_name(base: str, tag: str) -> str` → `f"{base}__{tag}"` (per-equipment copy carrying that equipment's AO image).
- `def ao_image_name(tag: str) -> str` → `f"{tag}_ao"`.

`scripts/blender/uvmath.py`:
- `def box_uv(co: tuple[float, float, float], normal: tuple[float, float, float], tile_m: float) -> tuple[float, float]` — world-space box projection: dominant axis of `|normal|` (ties → z, then x); z-dominant → `(x, y)`, x-dominant → `(y, z)`, y-dominant → `(x, z)`; each divided by `tile_m`.

`scripts/blender/layout.py`:
- `def to_local(item: dict[str, Any], world: tuple[float, float, float]) -> tuple[float, float, float]` — subtract `position_m`, rotate by `−rotation_deg` about z.
- `def to_world(item: dict[str, Any], local: tuple[float, float, float]) -> tuple[float, float, float]` — inverse of `to_local`.

## Pure-helper tests (full code)
`app/backend/tests/blender/test_spec_loader.py`:
```python
"""Tests for scripts/blender/spec_loader.py (runs in the uv env, no Blender)."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from plumetrace.config import REPO_ROOT

FACILITY_JSON = REPO_ROOT / "app/frontend/src/shared/facility/ks07.json"


def _load(name: str) -> ModuleType:
    """Import a module from scripts/blender by file path."""
    path = REPO_ROOT / "scripts" / "blender" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"blender_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_selects_spike_equipment_in_spec_order() -> None:
    """The spike selection returns K-202 and VS-250 with their anchors."""
    mod = _load("spec_loader")
    spec = mod.load_spec(FACILITY_JSON)
    items = mod.select_equipment(spec, frozenset({"VS-250", "K-202"}))
    assert [i["tag"] for i in items] == ["K-202", "VS-250"]
    assert ("VS-250.tip", (85.0, 115.0, 12.0)) in [
        (a, tuple(p)) for a, p in mod.anchors_of(items[1])
    ]


def test_unknown_tag_is_rejected() -> None:
    """A typo in --only fails loudly."""
    mod = _load("spec_loader")
    with pytest.raises(ValueError, match="unknown tag K-999"):
        mod.select_equipment(mod.load_spec(FACILITY_JSON), frozenset({"K-999"}))


def test_rejects_non_spec_json(tmp_path: Path) -> None:
    """A JSON file without equipment is not a facility spec."""
    mod = _load("spec_loader")
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"a": 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="missing equipment"):
        mod.load_spec(p)
```
`test_uvmath.py` (same `_load` helper, copy it): `box_uv((2.0, 4.0, 1.0), (0.0, 0.0, 1.0), 2.0) == (1.0, 2.0)`; `box_uv((2.0, 4.0, 6.0), (1.0, 0.0, 0.0), 2.0) == (2.0, 3.0)`; `box_uv((2.0, 4.0, 6.0), (0.0, -1.0, 0.0), 2.0) == (1.0, 3.0)`; a 45° normal `(0.7071, 0.0, 0.7071)` picks z → `(1.0, 2.0)` for `co=(2, 4, 6)`.
`test_layout.py`: with `item = {"position_m": [75, 75, 0], "rotation_deg": 90}`, `to_local(item, (75, 77, 1))` ≈ `(2, 0, 1)` (abs 1e-9) and `to_world(item, to_local(item, p)) ≈ p` for `p = (80.0, 70.0, 3.0)`.

## `scripts/check_glb.py` (repo tooling, uv env, stdlib only)
- `def read_glb_json(path: Path) -> dict[str, Any]` — validate header magic `b"glTF"`, version 2, first chunk type `JSON` (`0x4E4F534A`); return the parsed JSON chunk. Errors → `ValueError` with the reason.
- `def node_names(gltf: dict[str, Any]) -> set[str]`.
- `def required_names(spec: dict[str, Any], only: frozenset[str] | None) -> set[str]` — every selected equipment tag and every anchor id of those items.
- `def main(argv: Sequence[str] | None = None) -> int` — args `--glb PATH --spec PATH [--only TAGS] [--max-bytes N]`; prints `glb OK: <n> nodes, <bytes> bytes` and returns 0, or prints `missing nodes: <sorted list>` / `glb is <bytes> bytes, budget <N>` and returns 1.

`app/backend/tests/test_check_glb.py` — build a tiny GLB in the test (12-byte header + one JSON chunk padded to 4 bytes with spaces) containing nodes `K-202`, `K-202.packing`; assert `required_names` for `only={"K-202"}` includes `K-202.packing` and `K-202.engine_exhaust`, `main` returns 1 and prints `missing nodes: ['K-202.engine_exhaust']`; a file starting `b"glTX"` raises `ValueError`; `--max-bytes 10` returns 1.

## `scripts/fetch_polyhaven.py` (uv env, httpx 0.28.1)
- Reads `scripts/blender/polyhaven_manifest.json`:
```json
{
  "resolution": "1k",
  "textures": {
    "metal_plate": ["nor_gl", "Rough"],
    "concrete_floor_02": ["Diffuse", "nor_gl", "Rough"],
    "gravel_floor_02": ["Diffuse", "nor_gl", "Rough"],
    "corrugated_iron_02": ["Diffuse", "nor_gl", "Rough"],
    "metal_grate_rusty": ["Diffuse", "nor_gl", "Rough"]
  },
  "hdris": { "industrial_sunset_puresky": "hdr" },
  "sha256": {}
}
```
- For each texture: `GET https://api.polyhaven.com/files/<id>` → `data[<map>]["1k"]["jpg"]["url"]`; for the HDRI: `data["hdri"]["1k"]["hdr"]["url"]`. Only URLs starting `https://dl.polyhaven.org/` are accepted (else exit 1). Header `User-Agent: PlumeTrace-asset-fetch/1.0` (no personal data).
- Textures → `build/polyhaven/<id>/<file name from URL>`; HDRI → `app/frontend/public/textures/env/<file name>`.
- With `--record`, writes each file's SHA-256 into `sha256` (key = repo-relative path, sorted) and rewrites the manifest with `indent=2` + `\n`. Without it, every existing `sha256` entry must match (mismatch → exit 1 naming the file). First run: `--record`; commit the manifest.
- Skips files that already exist with the recorded hash.

## Blender package (bpy modules)
`build_station.py` — first lines:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
```
Then `main(argv)`: parse the arguments after `--` (`--spec PATH`, `--out PATH`, `--bake {none,low,high}`, `--only TAGS` comma-separated, `--textures DIR` default `build/polyhaven`); check `bpy.app.version[:2] == (4, 5)` else print `Blender 4.5 required, found <x.y.z>` and `sys.exit(2)`; `scene_setup.reset_scene()`; build ground; for each selected item call `equipment.BUILDERS[item["type"]](item, ctx)` (missing type → `sys.exit(f"no builder for type {type}")`); shelters for items with `shelter: true`; `materials.assign_all(ctx)`; `bake.bake_all(ctx, level)` unless `none`; `export.export_glb(out)`. Seeded randomness only: `random.Random(20261113)` in `ctx`.

`scene_setup.py`: `reset_scene()` = `bpy.ops.wm.read_factory_settings(use_empty=True)`; scene units metric, scale 1.0; `BuildContext` dataclass (`spec`, `textures_dir`, `rng`, `objects_by_tag: dict[str, list[Object]]`).

`parts/mesh_ops.py`: `box(name, size, location, rotation_z_deg=0)`, `cylinder(name, radius, depth, location, axis="Z", segments=24)`, `bevel_edges(obj, width_m, segments=2)` (Bevel modifier, `limit_method="ANGLE"`, applied at export via `export_apply=True`), `assign_box_uv(obj, tile_m)` (writes UV layer `UVMap` using `uvmath.box_uv` per loop), `parent_to(child, parent)`. Every mesh built with `bmesh` and `bpy.data.meshes.new`, never `bpy.ops.mesh.primitive_*`.

Geometry for the spike (all in metres, local to the item; `x` along the skid's long axis, `y` across, `z` up; positions converted with `layout.to_world`):

**K-202 (`equipment/compressor.py`, `size_m` 12 × 4 × 3)**
| Part | Shape | Size | Local position (centre) |
|---|---|---|---|
| skid | `parts/skid.py`: two W-beams along x (0.3 × 0.3 × 12 m, flange 0.02 m) + 5 cross-beams | 12 × 4 × 0.35 | z 0.175 |
| concrete pad | box, material `concrete` | 13 × 6.4 × 0.3 | z −0.15 (top flush with ground) |
| gas engine block | box, bevel 0.04 | 4.0 × 2.0 × 2.2 | x +3.5, z 1.45 |
| engine exhaust stack | cylinder r 0.18 | to z 6.0 | at the `K-202.engine_exhaust` anchor (x, y), base z 2.55 |
| crankcase | box, bevel 0.03 | 3.0 × 1.6 × 1.0 | x −1.5, z 0.85 (top at 1.35, below the packing manifold) |
| coupling guard | half-cylinder r 0.35, safety yellow | length 1.0 along x | x +1.0, z 1.2 |
| 4 cylinders | cylinder r 0.35, axis y | length 1.6 | x −2.5 and −0.5; y ±1.9; z 1.2 |
| 4 distance pieces | cylinder r 0.16, axis y | length 0.3 | y ±0.95 (fills crankcase face y ±0.8 to cylinder end y ±1.1), x as the cylinders, z 1.2 |
| suction bottle | horizontal vessel d 0.9 (`parts/vessel.py`) | length 5.0 along x | x −1.5, y −1.9, z 2.5 |
| discharge bottle | horizontal vessel d 0.8 | length 5.0 | x −1.5, y +1.9, z 2.5 |
| packing vent manifold | cylinder r 0.05, axis x | length 1.2 | **centred on the `K-202.packing` anchor** |
| packing vent riser | cylinder r 0.04 | from the manifold up to z 2.0 (the height of vent header R-250, built in Task 7) | manifold centre (local x −2.0 = world x 73, directly under R-250) |
| handrail (south side) | `parts/handrail.py`: posts every 1.5 m (r 0.025), top rail 1.1 m, knee rail 0.55 m, safety yellow | length 12 | y −3.0, base z 0 (on the pad, clear of the cylinders at y −2.7) |
| flanges | `parts/flange.py`: disc r = pipe r + 0.06, thickness 0.04 | — | both ends of each bottle and the riser |

**Shelter (`equipment/shelter.py`, for items with `shelter: true`)**: 6 columns (HEA 0.24 m square proxy boxes) at local x ∈ {−7, 0, +7}, y ∈ {−3.7, +3.7}, height 5.0; eaves beams along x; roof plane 15 × 8.4 m at z 5.0, pitch 5° rising toward +y, material `corrugated_iron_02` (tile 2 m); a half-height cladding wall (`corrugated_iron_02`) on the +y side from z 2.5 to 5.0; a 0.6 m roof opening is **not** modelled — the exhaust stack passes through the roof plane.

**VS-250 (`equipment/vent_stack.py`, `size_m` 0.4 × 0.4 × 12)**: base plate 1.0 × 1.0 × 0.05; stack cylinder r 0.2 from z 0.05 to 11.7; flanges at z 3, 6, 9; flame-arrestor body cylinder r 0.3, z 11.2–11.7; open tip ring (cylinder r 0.22, wall shown by a second inner cylinder with flipped normals) to z 12.0; 3 guy-wire lugs at z 9 (no wires in the spike). Inlet pipe stub r 0.1 from the base towards −y, 1.0 m.

**Ground (`equipment/ground.py`)**: spike patch 60 × 70 m centred on (80, 95) spec, `gravel_floor_02` tile 4 m; full station in Task 7.

**Anchors**: for every anchor of every built item, an empty (`bpy.data.objects.new(anchor_id, None)`, display size 0.2) at the anchor's world position, parented to the item's root object.

**Join rule** (`export.py` before export): per equipment, every static mesh part is joined into one object named exactly the tag (`naming.node_name`); separate-node parts (none in the spike) keep `naming.part_name`. Anchor empties stay children of that object.

## Materials (`materials.py`)
Principled BSDF, values in linear colour:
| key | Base colour | Roughness | Metallic | Textures |
|---|---|---|---|---|
| `paint_grey` | (0.50, 0.52, 0.50) | from `metal_plate_rough_1k` × 0.8 | 0.3 | `metal_plate_nor_gl_1k` normal (strength 0.6) |
| `paint_dark` (structure, skid) | (0.12, 0.13, 0.14) | 0.6 | 0.4 | same normal |
| `safety_yellow` | (0.78, 0.55, 0.03) | 0.55 | 0.1 | none |
| `concrete` | `concrete_floor_02` diffuse | its roughness | 0.0 | its normal |
| `gravel` | `gravel_floor_02` diffuse | its roughness | 0.0 | its normal |
| `cladding` | `corrugated_iron_02` diffuse | its roughness | 0.6 | its normal |
Texture coordinates: `UVMap` (box projection, tile 2 m unless stated). Each equipment gets its own copy of each material it uses (`naming.material_name`) because the copy carries that equipment's AO image.

## Bake (`bake.py`)
Per equipment object: add UV layer `AO` (keep `UVMap` active for rendering), make `AO` the active layer, edit mode → `bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=True, PREF_NEW_UVLAYER=False, PREF_MARGIN_DIV=0.2)` → object mode; image `naming.ao_image_name(tag)` 512² (`low`) / 1024² (`high`); in every material copy add an Image Texture node with that image, UV Map node `AO`, selected and active; Cycles, CPU, samples 16 (`low`) / 128 (`high`), `bpy.ops.object.bake(type="AO", margin=8, use_clear=True)` with only that object selected and active (other objects still occlude); `image.pack()`. Connect the image through a **Separate Color** node (R) into the `Occlusion` input of a node group named exactly `glTF Material Output` (create the group once with one float input `Occlusion`, as the 4.5 manual describes). The ground is baked too (512² both levels).

## Export (`export.py`)
`bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", export_yup=True, export_apply=True, export_texcoord=True, export_normals=True, export_materials="EXPORT", export_image_format="AUTO", export_cameras=False, export_lights=False, export_extras=False, use_selection=False)`.

Then optimise and check (from the repo root):
```bash
npx --yes @gltf-transform/cli@4.5.1 optimize build/ks07_raw.glb app/frontend/public/models/ks07.glb \
  --compress meshopt --texture-compress webp --texture-size 1024 \n  --join false --flatten false --simplify false --palette false --prune-leaves false
cd app && uv run python ../scripts/check_glb.py --glb frontend/public/models/ks07.glb \
  --spec frontend/src/shared/facility/ks07.json --only K-202,VS-250 --max-bytes 2000000
```
The five `false` flags keep every tag node, its hierarchy and the anchor empties (by default `optimize` joins meshes, flattens the tree and prunes empty leaf nodes — that would delete the anchors). Before the first run, check each flag exists in `npx --yes @gltf-transform/cli@4.5.1 optimize --help`; if one is missing, STOP and ask.
If the file is over 2 MB, rerun `optimize` with `--texture-size 512` once and record both sizes. Still over → the spike fails on size (report; do not tune further).

## Frontend viewer (minimal; Task 8 builds the full station view on top)
- `scene/coords.ts`: `specToScene([x, y, z]: readonly [number, number, number]): [number, number, number]` → `[x, z, -y]` (TSDoc explains Z-up spec vs Y-up three.js). Test `coords.test.ts`: `specToScene([75, 75, 0])` → `[75, 0, -75]`; `specToScene([85, 115, 12])` → `[85, 12, -115]`.
- `scene/reviewCamera.ts`: `REVIEW_CAMERA = { position: specToScene([45, 40, 25]), target: specToScene([80, 95, 3]), fov: 35 }` — the fixed camera for every screenshot and fps measurement in this project.
- `scene/EnvironmentMap.tsx`: drei `<Environment files="/textures/env/industrial_sunset_puresky_1k.hdr" background={false} environmentIntensity={0.8} />` plus `<color attach="background" args={["#a9b4bd"]} />` (a hazy sky grey; the HDRI is lighting only).
- `scene/Sun.tsx`: one `directionalLight` from the HDRI sun direction — spec azimuth 250° (WSW), elevation 18° → position = target + 150 m in that direction (compute with `specToScene`), intensity 2.5, colour `#ffd7a8`, `castShadow`, `shadow-mapSize` 2048 × 2048, orthographic shadow camera ±60 m around the target, `shadow-bias` −0.0005.
- `model/StationModel.tsx`: `useGLTF("/models/ks07.glb", false, true)` (second argument `false` = **no Draco**, which would download a decoder from a CDN; third `true` = meshopt, bundled). Traverse once in `useMemo`: meshes `castShadow = receiveShadow = true`. `<primitive object={scene} dispose={null} />`.
- `StationCanvas.tsx`: `<Canvas dpr={[1, 1.5]} shadows camera={{ position: REVIEW_CAMERA.position, fov: REVIEW_CAMERA.fov, near: 0.5, far: 2000 }} gl={{ antialias: true }} onCreated={({ camera }) => camera.lookAt(...REVIEW_CAMERA.target)}>` → `<Suspense fallback={null}>` → environment, sun, model. In dev only, `?perf` in the URL mounts `dev/PerfOverlay.tsx` (dynamic `import("r3f-perf")` behind `import.meta.env.DEV`).
- `StationView.tsx`: `React.lazy(() => import("./StationCanvas"))` inside `Suspense` (fallback: nothing) — mounted in AppShell's `<main aria-label="Station view">`; `index.ts` exports `StationView`.

## Pass / fail (record every number in `docs/evidence/2026-11-spike.md`)
| Check | Pass |
|---|---|
| Look | screenshot at `REVIEW_CAMERA`, 1920×1080, compared side by side with `docs/superpowers/specs/mockups/2026-11-12-3d-option-B-blender-baked.png`; **owner decides** |
| Frame rate | ≥ 58 fps average over 30 s after a 5 s warm-up, browser full-screen at 1920×1080, `?perf` overlay, on the owner's integrated-graphics laptop (record GPU string, browser + version) |
| Size | `ks07.glb` ≤ 2 MB (`check_glb.py` output) |
| Draw calls / triangles | from the perf overlay; record (no limit for the spike) |
| Bake time | wall-clock of `--bake high`; record |

## Steps
- [x] Confirm prerequisites (Blender version; download permission). STOP if either is missing.
- [x] Pure helpers + `check_glb.py`: tests → FAIL → implement → `uv run pytest app/backend -q` green; `uv run ruff check --config pyproject.toml ../scripts` clean.
- [x] `cd app && uv run python ../scripts/fetch_polyhaven.py --record`; commit the manifest and the HDRI.
- [x] Write the bpy modules. Run `blender --background --factory-startup --python scripts/blender/build_station.py -- --spec app/frontend/src/shared/facility/ks07.json --out build/ks07_raw.glb --bake low --only K-202,VS-250` until it completes without errors; then `--bake high`. Optimise + check (commands above).
- [x] Frontend: add deps (exact); coords test → FAIL → implement the viewer files; `npm run lint && npm run typecheck && npm run test && npm run build`.
- [x] Measure (table above) and take the screenshots: `docs/evidence/2026-11-spike-review.png` (review camera) and `docs/evidence/2026-11-spike-close.png` (orbit to 10 m from the distance pieces).
- [x] Repo checks (structure, secrets, env); `check_slop.py`.
- [x] **Docs.** `scripts/blender/README.md` (what each module does, the commands, Blender version, assets and licence, coordinate convention). FRONTEND.md → "3D station" (pipeline summary, coordinate mapping, review camera, no-Draco rule). `docs/reference/ASSETS.md` (new; add to `docs/README.md`): every Poly Haven asset, licence CC0, source URL, where it is used. Work-log with the measurements.
- [ ] **Commit** `feat(3d): add Blender spike for K-202 and VS-250`.
- [ ] `STATUS.md`: "Phase 4 Task 5 done — waiting for owner spike review (approach B go / no-go)". **STOP.** Owner answer **go** → next task `task-06-bpy-equipment.md`. Owner answer **no-go** → next task `task-05b-fallback-procedural.md`; Tasks 6–7 are then skipped.
