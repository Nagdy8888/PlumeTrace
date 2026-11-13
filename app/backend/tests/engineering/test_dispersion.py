"""Tests for the dispersion coefficient sets (hand calculations from the cited formulas)."""

import numpy as np
import pytest

from plumetrace.engineering.dispersion import CoefficientSet, sigmas_m
from plumetrace.engineering.stability import StabilityClass

BRIGGS = CoefficientSet.BRIGGS_RURAL
MARTIN = CoefficientSet.PG_MARTIN


def _one(x: float, s: StabilityClass, c: CoefficientSet) -> tuple[float, float]:
    sy, sz = sigmas_m(np.array([x]), s, c)
    return float(sy[0]), float(sz[0])


def test_briggs_class_d_at_1000_m() -> None:
    """Briggs D, x = 1000 m: sy = 80/sqrt(1.1) = 76.277 m; sz = 60/sqrt(2.5) = 37.947 m."""
    sy, sz = _one(1000.0, StabilityClass.D, BRIGGS)
    assert sy == pytest.approx(76.277, abs=0.01)
    assert sz == pytest.approx(37.947, abs=0.01)


def test_martin_class_d_at_500_m() -> None:
    """Martin D, x = 0.5 km: sy = 68*0.5^0.894 = 36.592 m; sz = 33.2*0.5^0.725 - 1.7 = 18.386 m."""
    sy, sz = _one(500.0, StabilityClass.D, MARTIN)
    assert sy == pytest.approx(36.592, abs=0.01)
    assert sz == pytest.approx(18.386, abs=0.01)


def test_martin_class_d_floor_near_source() -> None:
    """Martin D at 10 m gives sz = -0.52 m before the 0.5 m floor."""
    _, sz = _one(10.0, StabilityClass.D, MARTIN)
    assert sz == 0.5


def test_distance_is_clipped() -> None:
    """Distance x below 10 m behaves like 10 m; x above 1000 m behaves like 1000 m."""
    for c in (BRIGGS, MARTIN):
        assert _one(2.0, StabilityClass.C, c) == _one(10.0, StabilityClass.C, c)
        assert _one(5000.0, StabilityClass.C, c) == _one(1000.0, StabilityClass.C, c)


@pytest.mark.parametrize("coeff", [BRIGGS, MARTIN])
@pytest.mark.parametrize("stability", list(StabilityClass))
def test_sigmas_grow_with_distance(coeff: CoefficientSet, stability: StabilityClass) -> None:
    """Both sigmas are non-decreasing with downwind distance for every class and set."""
    sy, sz = sigmas_m(np.linspace(10.0, 1000.0, 50), stability, coeff)
    assert np.all(np.diff(sy) >= 0)
    assert np.all(np.diff(sz) >= 0)


def test_sets_differ_at_300_m() -> None:
    """The truth model must not equal the inversion model: at 300 m class D the sets differ."""
    b = _one(300.0, StabilityClass.D, BRIGGS)
    m = _one(300.0, StabilityClass.D, MARTIN)
    assert abs(b[1] - m[1]) / b[1] > 0.15
