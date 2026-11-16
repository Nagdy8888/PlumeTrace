"""Tests for scripts/blender/piping_math.py."""

import importlib.util
import math
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


def test_radius_has_a_visual_minimum() -> None:
    """2-inch lines are still visible; 24-inch lines are 0.3048 m in radius."""
    mod = _load("piping_math")
    assert mod.pipe_radius_m(2.0) == 0.03
    assert mod.pipe_radius_m(24.0) == pytest.approx(0.3048)


def test_fillet_keeps_endpoints_and_rounds_a_right_angle() -> None:
    """A 90-degree corner becomes an arc; the arc stays within the bend radius of the corner."""
    mod = _load("piping_math")
    pts = mod.fillet_polyline([(0.0, 0.0, 4.0), (10.0, 0.0, 4.0), (10.0, 10.0, 4.0)], 1.0, steps=6)
    assert pts[0] == (0.0, 0.0, 4.0) and pts[-1] == (10.0, 10.0, 4.0)
    assert len(pts) == 2 + 7
    assert all(math.dist(p, (10.0, 0.0, 4.0)) <= 1.0 + 1e-9 for p in pts[1:-1])


def test_fillet_ignores_collinear_points() -> None:
    """Straight runs are unchanged."""
    mod = _load("piping_math")
    pts = [(0.0, 0.0, 1.0), (5.0, 0.0, 1.0), (10.0, 0.0, 1.0)]
    assert mod.fillet_polyline(pts, 1.0) == pts


def test_supports_only_on_elevated_runs() -> None:
    """Supports every 6 m on the elevated part, none near the ends or below 1 m."""
    mod = _load("piping_math")
    sup = mod.support_points([(0.0, 0.0, 4.0), (30.0, 0.0, 4.0)])
    assert [p[0] for p in sup] == [6.0, 12.0, 18.0, 24.0]
    assert mod.support_points([(0.0, 0.0, 0.5), (30.0, 0.0, 0.5)]) == []


def test_fillet_is_capped_by_a_short_segment() -> None:
    """Added after the code: a 1 m leg limits the tangent distance to 0.45 m."""
    mod = _load("piping_math")
    pts = mod.fillet_polyline([(0.0, 0.0, 2.0), (10.0, 0.0, 2.0), (10.0, 1.0, 2.0)], 5.0, steps=4)
    assert pts[1][0] == pytest.approx(10.0 - 0.45)
    assert pts[-2][1] == pytest.approx(0.45)
    assert len(pts) == 2 + 5
