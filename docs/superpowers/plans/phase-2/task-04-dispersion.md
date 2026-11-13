# Phase 2 · Task 4 — Dispersion coefficient sets

**Skills:** `plan-execution`, `engineering-core`, `project-documentation`.

## Files
Create `app/backend/plumetrace/engineering/dispersion.py`, `app/backend/tests/engineering/test_dispersion.py`.

## Interface
- `class CoefficientSet(StrEnum)`: `BRIGGS_RURAL = "briggs_rural"`, `PG_MARTIN = "pg_martin"`
- `X_MIN_M: Final = 10.0`, `X_MAX_M: Final = 1000.0`, `SIGMA_MIN_M: Final = 0.5`
- `def sigmas_m(x_m: npt.NDArray[np.float64], stability: StabilityClass, coeff: CoefficientSet) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]` → `(sigma_y_m, sigma_z_m)`. Steps: clip `x_m` to `[X_MIN_M, X_MAX_M]`; evaluate the set; floor both results at `SIGMA_MIN_M`. Coefficients live in module-level `MappingProxyType` tables keyed by `StabilityClass`.

**BRIGGS_RURAL** (Briggs 1973, open country; Seinfeld & Pandis, *Atmospheric Chemistry and Physics*, 3rd ed., Table 18.3). x in m, σ in m.

| Class | σy | σz |
|---|---|---|
| A | `0.22·x·(1+0.0001x)^-0.5` | `0.20·x` |
| B | `0.16·x·(1+0.0001x)^-0.5` | `0.12·x` |
| C | `0.11·x·(1+0.0001x)^-0.5` | `0.08·x·(1+0.0002x)^-0.5` |
| D | `0.08·x·(1+0.0001x)^-0.5` | `0.06·x·(1+0.0015x)^-0.5` |
| E | `0.06·x·(1+0.0001x)^-0.5` | `0.03·x·(1+0.0003x)^-1` |
| F | `0.04·x·(1+0.0001x)^-0.5` | `0.016·x·(1+0.0003x)^-1` |

**PG_MARTIN** (Martin 1976 fit of the Pasquill–Gifford curves for x < 1 km; Cooper & Alley, *Air Pollution Control*, Table 20-1). `x_km = x/1000`; `σy = a·x_km^0.894`; `σz = c·x_km^d + f`.

| Class | a | c | d | f |
|---|---|---|---|---|
| A | 213 | 440.8 | 1.941 | 9.27 |
| B | 156 | 106.6 | 1.149 | 3.3 |
| C | 104 | 61.0 | 0.911 | 0.0 |
| D | 68 | 33.2 | 0.725 | −1.7 |
| E | 50.5 | 22.8 | 0.678 | −1.3 |
| F | 34 | 14.35 | 0.740 | −0.35 |

## Tests (full code) — `app/backend/tests/engineering/test_dispersion.py`
```python
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
    """x below 10 m behaves like 10 m; x above 1000 m behaves like 1000 m."""
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
```

## Steps
- [x] Test → FAIL → implement → full checks green.
- [x] **Docs.** ENGINEERING.md → "Dispersion coefficients": both tables with sources, clipping and floor, and the validity note ("classic fits are extrapolated below 100 m; the benchmark measures the consequence"). Work-log; `STATUS.md` (last 2.4, next 2.5).
- [ ] **Commit** `feat(engineering): add Briggs and Pasquill-Gifford dispersion coefficients`.
