"""Tests for scripts/blender/uvmath.py (runs in the uv env, no Blender)."""

import importlib.util
from types import ModuleType

from plumetrace.config import REPO_ROOT


def _load(name: str) -> ModuleType:
    """Import a module from scripts/blender by file path."""
    path = REPO_ROOT / "scripts" / "blender" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"blender_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_z_dominant_projects_to_xy() -> None:
    """A normal along +z maps (x, y) / tile."""
    mod = _load("uvmath")
    assert mod.box_uv((2.0, 4.0, 1.0), (0.0, 0.0, 1.0), 2.0) == (1.0, 2.0)


def test_x_dominant_projects_to_yz() -> None:
    """A normal along +x maps (y, z) / tile."""
    mod = _load("uvmath")
    assert mod.box_uv((2.0, 4.0, 6.0), (1.0, 0.0, 0.0), 2.0) == (2.0, 3.0)


def test_y_dominant_projects_to_xz() -> None:
    """A normal along -y maps (x, z) / tile (sign is ignored)."""
    mod = _load("uvmath")
    assert mod.box_uv((2.0, 4.0, 6.0), (0.0, -1.0, 0.0), 2.0) == (1.0, 3.0)


def test_diagonal_normal_ties_to_z() -> None:
    """A 45 degree x/z normal picks z."""
    mod = _load("uvmath")
    assert mod.box_uv((2.0, 4.0, 6.0), (0.7071, 0.0, 0.7071), 2.0) == (1.0, 2.0)
