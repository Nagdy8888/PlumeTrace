# Phase 2 · Task 5 — Gaussian plume forward model

**Skills:** `plan-execution`, `engineering-core`, `project-documentation`.

## Files
Create `app/backend/plumetrace/engineering/plume.py`, `app/backend/tests/engineering/test_plume.py`.

## Interface
- `def downwind_crosswind_m(source: Point3, receptors_xy: npt.NDArray[np.float64], wind_from_deg: float) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]`
  - `θ = radians(wind_from_deg + 180)` (direction the plume travels toward, clockwise from north);
  - `dx = receptors_xy[:, 0] − source.x_m`, `dy = receptors_xy[:, 1] − source.y_m`;
  - `along = dx·sin θ + dy·cos θ`; `cross = dx·cos θ − dy·sin θ`.
- `def concentration_kg_m3(rate_kg_s: float, wind_speed_m_s: float, wind_from_deg: float, source: Point3, receptors: npt.NDArray[np.float64], stability: StabilityClass, coeff: CoefficientSet) -> npt.NDArray[np.float64]`
  - `receptors` has shape `(N, 3)` (x, y, z in m); returns shape `(N,)`, concentration above background.
  - Raise `ValueError("wind_speed_m_s must be > 0")` if `wind_speed_m_s ≤ 0`; `ValueError("rate_kg_s must be >= 0")` if `rate_kg_s < 0`.
  - `σy, σz = sigmas_m(along, stability, coeff)` (sigmas clip `along` to `X_MIN_M` internally).
  - `C = Q / (2π·u·σy·σz) · exp(−cross²/(2σy²)) · [exp(−(z−H)²/(2σz²)) + exp(−(z+H)²/(2σz²))]` with `H = source.z_m`, `z = receptors[:, 2]`.
  - `C = 0` where `along ≤ 0`.
- `def concentration_ppm(rate_kg_s: float, wind_speed_m_s: float, wind_from_deg: float, source: Point3, receptors: npt.NDArray[np.float64], stability: StabilityClass, coeff: CoefficientSet, temp_k: float, pressure_pa: float) -> npt.NDArray[np.float64]` — `kg_m3_to_ppm(concentration_kg_m3(...), temp_k, pressure_pa)`.

Docstring of `concentration_kg_m3`: symbol table with units; assumptions (steady state over the
averaging period, flat terrain, no plume rise for vents, the 10 m wind used at all heights, total
ground reflection); reference: Turner, *Workbook of Atmospheric Dispersion Estimates*, 2nd ed., 1994.

## Tests (full code) — `app/backend/tests/engineering/test_plume.py`
```python
"""Tests for the Gaussian plume forward model (Turner 1994, eq. 1-1 with ground reflection)."""

import math

import numpy as np
import pytest

from plumetrace.engineering.dispersion import CoefficientSet, sigmas_m
from plumetrace.engineering.geometry import Point3
from plumetrace.engineering.plume import concentration_kg_m3, downwind_crosswind_m
from plumetrace.engineering.stability import StabilityClass

D = StabilityClass.D
BRIGGS = CoefficientSet.BRIGGS_RURAL
ORIGIN_GROUND = Point3(0.0, 0.0, 0.0)


def _c(rate: float, receptors: list[list[float]], wind_from: float = 270.0,
       source: Point3 = ORIGIN_GROUND, u: float = 4.0) -> np.ndarray:
    return concentration_kg_m3(rate, u, wind_from, source, np.array(receptors), D, BRIGGS)


def test_ground_source_centreline_matches_closed_form() -> None:
    """H = 0, z = 0 on the centreline: C = Q/(pi*u*sy*sz) (Turner 1994)."""
    sy, sz = sigmas_m(np.array([100.0]), D, BRIGGS)
    expected = 0.01 / (math.pi * 4.0 * float(sy[0]) * float(sz[0]))
    assert _c(0.01, [[100.0, 0.0, 0.0]])[0] == pytest.approx(expected, rel=1e-9)


def test_linear_in_emission_rate() -> None:
    """Doubling Q doubles every concentration."""
    rec = [[100.0, 5.0, 2.0], [60.0, -3.0, 1.5]]
    assert np.allclose(_c(0.02, rec), 2.0 * _c(0.01, rec))


def test_symmetric_across_the_plume_axis() -> None:
    """Receptors at +20 m and -20 m crosswind see the same concentration."""
    out = _c(0.01, [[100.0, 20.0, 2.0], [100.0, -20.0, 2.0]])
    assert out[0] == pytest.approx(out[1], rel=1e-12)


def test_upwind_receptors_are_zero() -> None:
    """Nothing is upwind of the source."""
    assert np.all(_c(0.01, [[-100.0, 0.0, 2.0], [-1.0, 50.0, 2.0]]) == 0.0)


def test_wind_direction_convention() -> None:
    """Wind FROM 270 deg (west) blows east; FROM 180 deg (south) blows north."""
    assert _c(0.01, [[100.0, 0.0, 2.0]], wind_from=270.0)[0] > 0.0
    assert _c(0.01, [[-100.0, 0.0, 2.0]], wind_from=270.0)[0] == 0.0
    assert _c(0.01, [[0.0, 100.0, 2.0]], wind_from=180.0)[0] > 0.0
    along, cross = downwind_crosswind_m(ORIGIN_GROUND, np.array([[0.0, 100.0]]), 180.0)
    assert along[0] == pytest.approx(100.0)
    assert cross[0] == pytest.approx(0.0, abs=1e-9)


def test_receptor_next_to_source_is_finite_and_clipped() -> None:
    """2 m downwind gives the same finite value as 10 m (distance clipped to 10 m)."""
    near = _c(0.01, [[2.0, 0.0, 0.0]])[0]
    ten = _c(0.01, [[10.0, 0.0, 0.0]])[0]
    assert math.isfinite(near)
    assert near == pytest.approx(ten, rel=1e-12)


def test_elevated_source_ground_reflection() -> None:
    """An elevated source gives a lower ground-level centreline value than a ground source."""
    ground = _c(0.01, [[50.0, 0.0, 0.0]])[0]
    stack = _c(0.01, [[50.0, 0.0, 0.0]], source=Point3(0.0, 0.0, 12.0))[0]
    assert 0.0 < stack < ground


def test_invalid_inputs_raise() -> None:
    """Zero wind and negative rates are rejected."""
    with pytest.raises(ValueError, match="wind_speed_m_s"):
        _c(0.01, [[100.0, 0.0, 2.0]], u=0.0)
    with pytest.raises(ValueError, match="rate_kg_s"):
        _c(-1.0, [[100.0, 0.0, 2.0]])


def test_vectorised_equals_loop() -> None:
    """1000 receptors at once equal 1000 single-receptor calls."""
    rng = np.random.default_rng(0)
    rec = np.column_stack([rng.uniform(-50, 300, 1000), rng.uniform(-100, 100, 1000),
                           rng.uniform(0, 5, 1000)])
    batch = concentration_kg_m3(0.01, 4.0, 250.0, Point3(5.0, 5.0, 2.0), rec, D, BRIGGS)
    loop = [concentration_kg_m3(0.01, 4.0, 250.0, Point3(5.0, 5.0, 2.0), r[None, :], D, BRIGGS)[0]
            for r in rec]
    assert np.allclose(batch, loop)
```

## Steps
- [x] Test → FAIL → implement → full checks green.
- [x] **Docs.** ENGINEERING.md → "Gaussian plume": the equation, symbol table with units, coordinate and wind conventions (with a small diagram in words), assumptions, limits, reference. Work-log; `STATUS.md` (last 2.5, next 2.6).
- [ ] **Commit** `feat(engineering): add Gaussian plume forward model`.
