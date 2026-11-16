"""Static checks of the Blender equipment builders (runs in the uv env, no Blender).

The builders need ``bpy``, so these tests read the source with ``ast``: they pin the registry, the
material keys and the owner rulings (C1 no tread-plate maps on paint, S311 no ``random`` module)
without building geometry. Geometry is checked by the Blender runs in the work log. Written after
the builders, so not red-first.
"""

import ast
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from plumetrace.config import REPO_ROOT

BLENDER = REPO_ROOT / "scripts" / "blender"
SPEC = REPO_ROOT / "app" / "frontend" / "src" / "shared" / "facility" / "ks07.json"
PAINTED = ("paint_grey", "paint_dark", "paint_red", "paint_white", "pipe_gas")


def _tree(path: Path) -> ast.Module:
    """Parse a source file."""
    return ast.parse(path.read_text(encoding="utf-8"))


def _assigned_value(path: Path, name: str) -> ast.expr:
    """Value of the module-level assignment ``name = ...`` (plain or annotated)."""
    for node in _tree(path).body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == name:
            assert node.value is not None
            return node.value
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == name:
            return node.value
    raise AssertionError(f"{name} not assigned in {path}")


def _specs() -> dict[str, ast.Call]:
    """The ``SPECS`` table of materials.py: material key to its ``_spec(...)`` call."""
    table = _assigned_value(BLENDER / "materials.py", "SPECS")
    assert isinstance(table, ast.Dict)
    return {
        k.value: v
        for k, v in zip(table.keys, table.values, strict=True)
        if isinstance(k, ast.Constant) and isinstance(v, ast.Call)
    }


def _load(name: str) -> ModuleType:
    """Import a pure module from scripts/blender by file path."""
    spec = importlib.util.spec_from_file_location(f"blender_{name}", BLENDER / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_equipment_type_has_a_builder() -> None:
    """Every ``type`` of ks07.json is a key of ``BUILDERS`` and no key is unused (15 types)."""
    registry = _assigned_value(BLENDER / "equipment" / "__init__.py", "BUILDERS")
    assert isinstance(registry, ast.Dict)
    keys = {k.value for k in registry.keys if isinstance(k, ast.Constant)}
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    types = {item["type"] for item in spec["equipment"]}
    assert keys == types
    assert len(types) == 15


def test_builders_only_ask_for_known_material_keys() -> None:
    """Every literal material key passed to ``add_part`` / ``add_node_part`` is in ``SPECS``."""
    known = set(_specs())
    used: set[str] = set()
    for path in [*(BLENDER / "equipment").glob("*.py"), *(BLENDER / "parts").glob("*.py")]:
        for node in ast.walk(_tree(path)):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            if node.func.attr in ("add_part", "add_node_part") and len(node.args) > 2:
                arg = node.args[2]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    used.add(arg.value)
    assert used, "no add_part calls found: the scan is broken"
    assert used <= known, sorted(used - known)


def test_painted_materials_have_no_texture_maps() -> None:
    """C1 (owner ruling): paint and gas-pipe materials use a constant roughness, no tread plate."""
    specs = _specs()
    for key in PAINTED:
        keywords = {kw.arg for kw in specs[key].keywords}
        assert keywords.isdisjoint({"normal", "rough_tex", "diffuse"}), key
        assert "rough" in keywords, key


def test_paint_grey_roughness_is_constant_half() -> None:
    """C1: ``paint_grey`` has constant roughness 0.5."""
    call = _specs()["paint_grey"]
    rough = next(kw.value for kw in call.keywords if kw.arg == "rough")
    assert isinstance(rough, ast.Constant) and rough.value == 0.5


@pytest.mark.parametrize("folder", ["equipment", "parts", "."])
def test_no_random_module(folder: str) -> None:
    """S311 (owner ruling): variation comes from the numpy ``ctx.rng``, never ``random``."""
    for path in (BLENDER / folder).glob("*.py"):
        for node in ast.walk(_tree(path)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else []
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            assert "random" not in names, path.name


def test_separate_node_names() -> None:
    """The fan and flare-tip nodes are ``<tag>__<part>`` (the names the frontend looks up)."""
    naming = _load("naming")
    assert naming.part_name("E-231", "fan_1") == "E-231__fan_1"
    assert naming.part_name("FL-601", "tip") == "FL-601__tip"
