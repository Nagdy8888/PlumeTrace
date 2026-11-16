"""Build the baked station glb from the facility spec (run inside Blender, headless).

Run from the repo root::

    blender --background --factory-startup --python scripts/blender/build_station.py -- \
        --spec app/frontend/src/shared/facility/ks07.json --out build/ks07_raw.glb \
        --bake low --only K-202,VS-250 [--still build/stills/recip_compressor.png]

Blender 4.5 LTS only. Seeded randomness only; rerunning reproduces the model.
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

SEED = 20261113


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the arguments after ``--`` (Blender keeps its own before it)."""
    parser = argparse.ArgumentParser(prog="build_station")
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bake", choices=["none", "low", "high"], default="low")
    parser.add_argument("--only", default="", help="comma-separated tags (default: all)")
    parser.add_argument("--textures", type=Path, default=Path("build/polyhaven"))
    parser.add_argument("--still", type=Path, help="render a review PNG of the first --only tag")
    return parser.parse_args(argv[argv.index("--") + 1 :] if "--" in argv else [])


def main(argv: list[str]) -> None:
    """Build, bake and export.

    Args:
        argv: Full command line (``sys.argv``).
    """
    import bake
    import bpy
    import equipment
    import export
    import materials
    import scene_setup
    import still
    from equipment import ground, shelter
    from spec_loader import load_spec, select_equipment

    args = parse_args(argv)
    if bpy.app.version[:2] != (4, 5):
        print(f"Blender 4.5 required, found {'.'.join(map(str, bpy.app.version))}")
        sys.exit(2)
    started = time.monotonic()
    only = frozenset(t for t in args.only.split(",") if t) or None
    spec = load_spec(args.spec)
    items = select_equipment(spec, only)
    scene_setup.reset_scene()
    ctx = scene_setup.BuildContext(spec, args.textures.resolve(), np.random.default_rng(SEED))
    ground.build_ground(ctx)
    for item in items:
        builder = equipment.BUILDERS.get(item["type"])
        if builder is None:
            sys.exit(f"no builder for type {item['type']}")
        builder(item, ctx)
        if item.get("shelter"):
            shelter.build_shelter(item, ctx)
    materials.assign_all(ctx)
    export.add_anchors(ctx)
    export.join_equipment(ctx)
    if args.still is not None:
        still.render_still(items[0], args.still.resolve())
    bake_s = 0.0
    if args.bake != "none":
        bake_s = bake.bake_all(ctx, args.bake)
    export.export_glb(args.out.resolve())
    print(
        f"build_station: {args.out} bake={args.bake} bake_s={bake_s:.1f} "
        f"total_s={time.monotonic() - started:.1f}"
    )


if __name__ == "__main__":
    main(sys.argv)
