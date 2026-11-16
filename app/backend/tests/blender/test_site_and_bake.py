"""Static checks of the Task 7 Blender modules (site, piping, bake) and of build_station.sh.

These modules need ``bpy``, so the tests read the source with ``ast`` or as text: they pin the
owner rulings (C1 no tread plate on pipes, C2 gravel factor band, C3 smart project unwrap,
``ao_resolution`` wired, plan corrections in the shell script) without building geometry.
Geometry and bake results are checked by the Blender runs in the work log. Written after the
code, so not red-first, except the two fence-post tests (pure ``fence_math``), which were seen red
against the first post maths in the fix round.
"""

import ast
import importlib.util
import json
import re
from pathlib import Path

from plumetrace.config import REPO_ROOT

BLENDER = REPO_ROOT / "scripts" / "blender"
SPEC = REPO_ROOT / "app" / "frontend" / "src" / "shared" / "facility" / "ks07.json"
PIPE_KEYS = ("pipe_gas", "pipe_vent", "pipe_condensate", "pipe_fuel")


def _assigned(path: Path, name: str) -> ast.expr:
    """Value of the module-level assignment ``name = ...`` (plain or annotated)."""
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == name:
            assert node.value is not None
            return node.value
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == name:
            return node.value
    raise AssertionError(f"{name} not assigned in {path}")


def _specs() -> dict[str, dict[str, ast.expr]]:
    """``SPECS`` of materials.py: material key to the keyword arguments of its ``_spec`` call."""
    table = _assigned(BLENDER / "materials.py", "SPECS")
    assert isinstance(table, ast.Dict)
    return {
        k.value: {kw.arg: kw.value for kw in v.keywords if kw.arg}
        for k, v in zip(table.keys, table.values, strict=True)
        if isinstance(k, ast.Constant) and isinstance(v, ast.Call)
    }


def test_pipe_and_site_materials_exist_without_texture_maps() -> None:
    """C1 applied to every pipe material and the asphalt: constant roughness, no maps."""
    specs = _specs()
    for key in (*PIPE_KEYS, "asphalt"):
        assert {"normal", "rough_tex", "diffuse"}.isdisjoint(specs[key]), key
        assert "rough" in specs[key], key


def test_pipe_service_materials_cover_the_spec() -> None:
    """Every service used by a spec route maps to an existing material key."""
    mapping = _assigned(BLENDER / "equipment" / "pipe_route.py", "SERVICE_MATERIAL")
    assert isinstance(mapping, ast.Dict)
    services = {
        k.value: v.value
        for k, v in zip(mapping.keys, mapping.values, strict=True)
        if isinstance(k, ast.Constant) and isinstance(v, ast.Constant)
    }
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert {r["service"] for r in spec["piping"]} <= set(services)
    assert set(services.values()) <= set(_specs())


def test_gravel_factor_is_in_the_ruled_band() -> None:
    """C2 (owner ruling): the gravel diffuse multiplier is between 0.4 and 0.7, on both gravels."""
    factor = _assigned(BLENDER / "materials.py", "GRAVEL_FACTOR")
    assert isinstance(factor, ast.Constant)
    assert 0.4 <= factor.value <= 0.7
    specs = _specs()
    for key in ("gravel", "gravel_far"):
        assert isinstance(specs[key]["diffuse_factor"], ast.Name)
        assert specs[key]["diffuse_factor"].id == "GRAVEL_FACTOR"
    far_rough = specs["gravel_far"]["rough"]
    assert isinstance(far_rough, ast.Constant) and far_rough.value == 1.0


def test_bake_uses_smart_project_and_ao_resolution() -> None:
    """C3 (owner ruling): smart project with a 0.02 margin; ``ao_resolution`` is wired in."""
    text = (BLENDER / "bake.py").read_text(encoding="utf-8")
    assert "uv.smart_project" in text
    assert "lightmap_pack" not in text
    assert re.search(r"UNWRAP_MARGIN = 0\.02\b", text)
    assert "ao_resolution(" in text
    assert "PIPE_PREFIX" in text  # piping routes are not baked


def test_site_pads_skip_the_types_with_their_own_pad() -> None:
    """Pads are added for every type except the three whose builders have a pad of their own."""
    own = _assigned(BLENDER / "equipment" / "site.py", "OWN_PAD_TYPES")
    names = {c.value for c in ast.walk(own) if isinstance(c, ast.Constant)}
    assert names == {"recip_compressor", "pig_trap", "building"}
    for tag in ("compressor", "pig_trap"):
        assert "_pad" in (BLENDER / "equipment" / f"{tag}.py").read_text(encoding="utf-8")


def test_site_node_names() -> None:
    """The site and pipe node names the glb and the tests rely on."""
    naming = BLENDER / "naming.py"
    names = {
        n: _assigned(naming, n) for n in ("GROUND_TAG", "RACKS_TAG", "FENCE_TAG", "PIPE_PREFIX")
    }
    assert [c.value for c in names.values() if isinstance(c, ast.Constant)] == [
        "SITE__ground",
        "SITE__racks",
        "SITE__fence",
        "PIPE__",
    ]


def test_build_script_has_the_owner_corrected_flags() -> None:
    """The one-command script uses ``--prune false`` (not ``--prune-leaves``) and the budgets."""
    text = (REPO_ROOT / "scripts" / "build_station.sh").read_text(encoding="utf-8")
    assert "--prune false" in text
    assert "--prune-leaves" not in text
    assert "--max-bytes 15000000" in text
    assert "--max-triangles 1500000" in text
    assert "--max-draw-calls 300" in text
    assert "Blender 4\\.5\\.16" in text


def _fence_posts() -> list[tuple[float, float]]:
    """Posts from the pure ``fence_math`` module with the site's yard, spacing and gate."""
    path = BLENDER / "fence_math.py"
    spec = importlib.util.spec_from_file_location("blender_fence_math", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yard = _assigned(BLENDER / "equipment" / "site.py", "YARD_M")
    assert isinstance(yard, ast.Tuple)
    width, depth = (float(ast.literal_eval(e)) for e in yard.elts)
    return module.fence_post_xy(width, depth, 3.0, (9.0, 15.0))


def test_fence_posts_stay_inside_the_yard_and_hit_every_corner_once() -> None:
    """Posts every 3 m on the four bounds, none outside x 0-200 / y 0-150 (review finding).

    The first version counted ``round(200 / 3) + 1`` posts along x, which ran to x = 201 and put
    two stray posts at (201, 0) and (201, 150). Red against that version, green after the fix.
    """
    posts = _fence_posts()
    assert len(posts) == len(set(posts)) == 233
    assert all(0.0 <= x <= 200.0 and 0.0 <= y <= 150.0 for x, y in posts)
    for corner in ((0.0, 0.0), (200.0, 0.0), (0.0, 150.0), (200.0, 150.0)):
        assert posts.count(corner) == 1, corner
    assert all(x in (0.0, 200.0) or y in (0.0, 150.0) for x, y in posts)


def test_fence_post_spacing_is_at_most_3_m_and_the_gate_stays_open() -> None:
    """Neighbouring posts on a side are at most 3 m apart; no post inside x 0, y 9 to 15."""
    posts = _fence_posts()
    south = sorted(x for x, y in posts if y == 0.0)
    east = sorted(y for x, y in posts if x == 200.0)
    west = sorted(y for x, y in posts if x == 0.0)
    for values in (south, east):
        assert max(b - a for a, b in zip(values, values[1:], strict=False)) <= 3.0
    assert not any(9.0 < y < 15.0 for y in west)
    assert {9.0, 15.0} <= set(west)
