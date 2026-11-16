"""Tests for scripts/blender/layout.py (runs in the uv env, no Blender)."""

import importlib.util
from types import ModuleType

import pytest

from plumetrace.config import REPO_ROOT


def _load(name: str) -> ModuleType:
    """Import a module from scripts/blender by file path."""
    path = REPO_ROOT / "scripts" / "blender" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"blender_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ITEM = {"position_m": [75, 75, 0], "rotation_deg": 90}


def test_to_local_rotates_by_minus_rotation() -> None:
    """A point 2 m north of an item rotated 90 degrees is 2 m along its local x."""
    mod = _load("layout")
    local = mod.to_local(ITEM, (75, 77, 1))
    assert local == pytest.approx((2, 0, 1), abs=1e-9)


def test_round_trip() -> None:
    """to_world inverts to_local."""
    mod = _load("layout")
    p = (80.0, 70.0, 3.0)
    assert mod.to_world(ITEM, mod.to_local(ITEM, p)) == pytest.approx(p, abs=1e-9)


def test_ao_resolution_budget() -> None:
    """Large items get 1024 px AO at high quality, the rest 512 px; low is always 256 px."""
    mod = _load("layout")
    assert mod.ao_resolution("recip_compressor", "high") == 1024
    assert mod.ao_resolution("ground", "high") == 1024
    assert mod.ao_resolution("storage_tank", "high") == 512
    assert mod.ao_resolution("flare_stack", "low") == 256
    with pytest.raises(ValueError):
        mod.ao_resolution("vru", "ultra")
