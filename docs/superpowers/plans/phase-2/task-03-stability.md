# Phase 2 · Task 3 — Atmospheric stability class (Pasquill–Gifford–Turner)

**Skills:** `plan-execution`, `engineering-core`, `project-documentation`.

## Files
Create `app/backend/plumetrace/engineering/stability.py`, `app/backend/tests/engineering/test_stability.py`.

## Interface
- `class StabilityClass(StrEnum)`: `A = "A"`, `B = "B"`, `C = "C"`, `D = "D"`, `E = "E"`, `F = "F"`
- Constants (`Final[float]`): `DAY_SHORTWAVE_W_M2 = 10.0`, `STRONG_W_M2 = 600.0`, `MODERATE_W_M2 = 300.0`, `OVERCAST_FRACTION = 0.875`, `NIGHT_CLOUDY_FRACTION = 0.5`
- `def pasquill_class(wind_speed_m_s: float, shortwave_w_m2: float, cloud_fraction: float) -> StabilityClass`

Rules — implement with lookup tables (dicts), not nested ifs. Split classes of the classic table are resolved to the **more stable** letter (document why: conservative, higher predicted concentrations).
1. `cloud_fraction ≥ 0.875` (overcast), day or night → `D`.
2. Day = `shortwave_w_m2 > 10.0`. Insolation: strong `> 600`, moderate `300 ≤ s ≤ 600`, slight `< 300`.
3. Night: cloudy = `cloud_fraction ≥ 0.5`, clear otherwise.
4. Wind bins: `u < 2`, `2 ≤ u < 3`, `3 ≤ u < 5`, `5 ≤ u < 6`, `u ≥ 6`.

| u (m/s) | day strong | day moderate | day slight | night cloudy | night clear |
|---|---|---|---|---|---|
| < 2 | A | B | B | F | F |
| 2 – < 3 | B | B | C | E | F |
| 3 – < 5 | B | C | C | D | E |
| 5 – < 6 | C | D | D | D | D |
| ≥ 6 | C | D | D | D | D |

## Tests (full code) — `app/backend/tests/engineering/test_stability.py`
```python
"""Tests for the Pasquill-Gifford-Turner stability table (Turner 1994, Table 1-1)."""

import pytest

from plumetrace.engineering.stability import StabilityClass as S
from plumetrace.engineering.stability import pasquill_class

# (wind m/s, shortwave W/m2, cloud fraction) -> class; one case per table cell.
CELLS = [
    ((1.0, 700.0, 0.1), S.A), ((1.0, 400.0, 0.1), S.B), ((1.0, 100.0, 0.1), S.B),
    ((2.5, 700.0, 0.1), S.B), ((2.5, 400.0, 0.1), S.B), ((2.5, 100.0, 0.1), S.C),
    ((4.0, 700.0, 0.1), S.B), ((4.0, 400.0, 0.1), S.C), ((4.0, 100.0, 0.1), S.C),
    ((5.5, 700.0, 0.1), S.C), ((5.5, 400.0, 0.1), S.D), ((5.5, 100.0, 0.1), S.D),
    ((7.0, 700.0, 0.1), S.C), ((7.0, 400.0, 0.1), S.D), ((7.0, 100.0, 0.1), S.D),
    ((1.0, 0.0, 0.6), S.F), ((1.0, 0.0, 0.2), S.F),
    ((2.5, 0.0, 0.6), S.E), ((2.5, 0.0, 0.2), S.F),
    ((4.0, 0.0, 0.6), S.D), ((4.0, 0.0, 0.2), S.E),
    ((5.5, 0.0, 0.6), S.D), ((5.5, 0.0, 0.2), S.D),
]


@pytest.mark.parametrize(("inputs", "expected"), CELLS)
def test_every_table_cell(inputs: tuple[float, float, float], expected: S) -> None:
    """Each cell of the table maps to the documented class."""
    assert pasquill_class(*inputs) == expected


def test_overcast_is_neutral_day_and_night() -> None:
    """Overcast (>= 7/8 cloud) is class D regardless of sun and wind."""
    assert pasquill_class(1.0, 900.0, 0.9) == S.D
    assert pasquill_class(1.0, 0.0, 0.9) == S.D


@pytest.mark.parametrize(
    ("inputs", "expected"),
    [
        ((2.0, 700.0, 0.1), S.B),  # u = 2 belongs to the 2-<3 bin
        ((3.0, 700.0, 0.1), S.B),  # u = 3 belongs to the 3-<5 bin
        ((4.0, 600.0, 0.1), S.C),  # 600 W/m2 is moderate, not strong
        ((4.0, 300.0, 0.1), S.C),  # 300 W/m2 is moderate
        ((4.0, 10.0, 0.2), S.E),   # 10 W/m2 is night
        ((4.0, 0.0, 0.5), S.D),    # cloud 0.5 counts as cloudy at night
    ],
)
def test_bin_boundaries(inputs: tuple[float, float, float], expected: S) -> None:
    """Boundary values fall into the documented bins."""
    assert pasquill_class(*inputs) == expected
```

## Steps
- [ ] Test → FAIL → implement → full checks green.
- [ ] **Docs.** ENGINEERING.md → "Stability": the table, bins, thresholds, the more-stable resolution rule and why. Work-log; `STATUS.md` (last 2.3, next 2.4).
- [ ] **Commit** `feat(engineering): add Pasquill stability classification`.
