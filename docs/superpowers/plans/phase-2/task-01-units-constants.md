# Phase 2 · Task 1 — Constants and unit conversions

**Skills:** `plan-execution`, `engineering-core`, `project-documentation`.

## Files
| Action | Path |
|---|---|
| Modify | `app/backend/pyproject.toml` → add `"numpy==2.5.4"` to `dependencies` |
| Create | `app/backend/plumetrace/engineering/constants.py`, `app/backend/plumetrace/engineering/units.py` |
| Create | `app/backend/tests/engineering/test_units.py` |
| Create | `docs/reference/ENGINEERING.md` (sections are added by every Phase 2 task); add its row to `docs/README.md` |

## Interface

`constants.py` (each constant with a `# source:` comment; type `Final[float]`):
| Name | Value | Source comment |
|---|---|---|
| `R_J_MOL_K` | `8.314462618` | CODATA 2018 molar gas constant |
| `M_CH4_KG_MOL` | `0.016043` | NIST Chemistry WebBook, methane |
| `T_STD_K` | `288.15` | ISO 13443 standard reference conditions (15 °C) |
| `P_STD_PA` | `101325.0` | ISO 13443 standard reference conditions |
| `FT3_TO_M3` | `0.028316846592` | exact (1 ft = 0.3048 m) |
| `GWP100_CH4_FOSSIL` | `29.8` | IPCC AR6 WG1 Ch. 7, Table 7.15 (fossil CH4) |
| `GWP20_CH4_FOSSIL` | `82.5` | IPCC AR6 WG1 Ch. 7, Table 7.15 (fossil CH4) |
| `BACKGROUND_PPM` | `1.95` | approximate global mean surface CH4 (design §5) |
| `HOURS_PER_YEAR` | `8760.0` | non-leap year |

`units.py`:
- `FloatOrArray = float | npt.NDArray[np.float64]` (type alias)
- `def kg_h_to_kg_s(rate_kg_h: float) -> float` (÷ 3600)
- `def kg_s_to_kg_h(rate_kg_s: float) -> float` (× 3600)
- `def kg_m3_to_ppm(conc_kg_m3: FloatOrArray, temp_k: float, pressure_pa: float, molar_mass_kg_mol: float = M_CH4_KG_MOL) -> FloatOrArray` — ideal gas: `conc · R · T / (P · M) · 1e6`
- `def ppm_to_kg_m3(conc_ppm: FloatOrArray, temp_k: float, pressure_pa: float, molar_mass_kg_mol: float = M_CH4_KG_MOL) -> FloatOrArray` — inverse
- `def scf_to_sm3(volume_scf: float) -> float` — `× FT3_TO_M3` (docstring: the 60 °F vs 15 °C reference difference, ~0.2 %, is ignored)
- `def kg_h_to_t_yr(rate_kg_h: float) -> float` — `× HOURS_PER_YEAR / 1000`
- `def co2e_kg(ch4_kg: float, horizon: Literal["GWP100", "GWP20"]) -> float`

## Tests (full code) — `app/backend/tests/engineering/test_units.py`
```python
"""Tests for engineering constants and unit conversions."""

import numpy as np
import pytest

from plumetrace.engineering import constants as c
from plumetrace.engineering.units import (
    co2e_kg,
    kg_h_to_kg_s,
    kg_h_to_t_yr,
    kg_m3_to_ppm,
    kg_s_to_kg_h,
    ppm_to_kg_m3,
    scf_to_sm3,
)


def test_constant_values() -> None:
    """Constants match their cited sources exactly."""
    assert c.R_J_MOL_K == 8.314462618
    assert c.M_CH4_KG_MOL == 0.016043
    assert (c.T_STD_K, c.P_STD_PA) == (288.15, 101325.0)
    assert (c.GWP100_CH4_FOSSIL, c.GWP20_CH4_FOSSIL) == (29.8, 82.5)
    assert c.BACKGROUND_PPM == 1.95


def test_rate_conversions() -> None:
    """kg/h <-> kg/s and kg/h -> t/yr."""
    assert kg_h_to_kg_s(3600.0) == 1.0
    assert kg_s_to_kg_h(1.0) == 3600.0
    assert kg_h_to_t_yr(1.0) == pytest.approx(8.76)


def test_pure_methane_density_at_standard_conditions() -> None:
    """1e6 ppm CH4 at 288.15 K, 101325 Pa equals P*M/(R*T) = 0.67850 kg/m3 (ideal gas law)."""
    assert ppm_to_kg_m3(1e6, c.T_STD_K, c.P_STD_PA) == pytest.approx(0.67850, rel=1e-4)


def test_ppm_round_trip() -> None:
    """ppm -> kg/m3 -> ppm returns the input."""
    value = ppm_to_kg_m3(10.0, 298.15, 101325.0)
    assert kg_m3_to_ppm(value, 298.15, 101325.0) == pytest.approx(10.0)


def test_array_input_keeps_shape() -> None:
    """Vectorised input returns an array of the same shape."""
    out = ppm_to_kg_m3(np.array([1.0, 2.0]), 298.15, 101325.0)
    assert isinstance(out, np.ndarray)
    assert out.shape == (2,)


def test_scf_and_co2e() -> None:
    """Standard cubic feet and CO2-equivalent conversions."""
    assert scf_to_sm3(1.0) == pytest.approx(0.028316846592)
    assert co2e_kg(1.0, "GWP100") == 29.8
    assert co2e_kg(2.0, "GWP20") == pytest.approx(165.0)
```

## Steps
- [ ] **1.** Add numpy to `app/backend/pyproject.toml`; `cd app && uv sync`.
- [ ] **2.** Write the test → `uv run pytest backend/tests/engineering/test_units.py -q` fails (import error).
- [ ] **3.** Implement `constants.py` and `units.py` (Google docstrings with units).
- [ ] **4.** Full checks green (pytest all, ruff, ruff format, mypy, repo checks).
- [ ] **5. Docs.** Create `docs/reference/ENGINEERING.md` using the reference-page template from `project-documentation` (sections 1–9) with a "Units and constants" subsection: table of every constant (value, unit, source), the conversion functions and their formulas. Add the row to `docs/README.md`. Work-log; `STATUS.md` (last 2.1, next 2.2).
- [ ] **6. Commit** `feat(engineering): add constants and unit conversions`.
