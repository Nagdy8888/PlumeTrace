# Phase 2 · Task 10 — Flare methane slip and blowdown vented mass

**Skills:** `plan-execution`, `engineering-core`, `project-documentation`.

## Files
Create `app/backend/plumetrace/engineering/flare.py`, `app/backend/plumetrace/engineering/blowdown.py`, `app/backend/tests/engineering/test_flare.py`, `app/backend/tests/engineering/test_blowdown.py`.

## Interface
`flare.py`:
- `DEFAULT_DESTRUCTION_EFFICIENCY: Final = 0.98` — source comment: "98 % destruction and removal efficiency, the default for a lit, well-operated flare in OGMP 2.0 guidance and EPA AP-42 §13.5; real efficiency varies with wind and flow (design §5.3)".
- `def flare_ch4_slip_kg_h(flared_gas_kg_h: float, ch4_mass_fraction: float, pilot_lit: bool, destruction_efficiency: float = DEFAULT_DESTRUCTION_EFFICIENCY) -> float` — lit: `(1 − DE) · flared · w`; unlit: `flared · w`. Raise `ValueError` for negative flow, `w` outside `[0, 1]` or `DE` outside `[0, 1]`.

`blowdown.py`:
- `class BlowdownResult(BaseModel)` (frozen): `gas_mass_kg: float`, `ch4_mass_kg: float`.
- `def vented_mass(volume_m3: float, p_initial_pa: float, t_initial_k: float, p_final_pa: float, t_final_k: float, comp: GasComposition) -> BlowdownResult` — `gas = V · (ρ(p_i, T_i) − ρ(p_f, T_f))` with `density_kg_m3`; `ch4 = gas · ch4_mass_fraction(comp)`. Raise `ValueError("volume_m3 must be > 0")` and `ValueError("p_final_pa must not exceed p_initial_pa")`.

## Tests (full code)

`app/backend/tests/engineering/test_flare.py`:
```python
"""Tests for flare methane slip."""

import pytest

from plumetrace.engineering.flare import flare_ch4_slip_kg_h


def test_unlit_flare_vents_all_methane() -> None:
    """Pilot out: every kg of methane sent to the flare is emitted (100 * 0.8624 = 86.24)."""
    assert flare_ch4_slip_kg_h(100.0, 0.8624, pilot_lit=False) == pytest.approx(86.24)


def test_lit_flare_slips_two_percent() -> None:
    """Lit flare at 98 % destruction: 2 % of 86.24 = 1.7248 kg/h."""
    assert flare_ch4_slip_kg_h(100.0, 0.8624, pilot_lit=True) == pytest.approx(1.7248)


def test_invalid_inputs() -> None:
    """Negative flow and impossible fractions are rejected."""
    with pytest.raises(ValueError):
        flare_ch4_slip_kg_h(-1.0, 0.8, pilot_lit=True)
    with pytest.raises(ValueError):
        flare_ch4_slip_kg_h(1.0, 1.2, pilot_lit=True)
```

`app/backend/tests/engineering/test_blowdown.py`:
```python
"""Tests for blowdown vented mass (KS-07 gas; hand calculation in the docstring)."""

import pytest

from plumetrace.engineering.blowdown import vented_mass
from plumetrace.engineering.gas import GasComposition, ch4_mass_fraction

KS07 = GasComposition(
    mole_fractions={"CH4": 0.930, "C2H6": 0.035, "C3H8": 0.008, "nC4H10": 0.002,
                    "CO2": 0.010, "N2": 0.015}
)


def test_ten_cubic_metres_from_discharge_pressure() -> None:
    """10 m3 from 7.0 MPa/300 K to 98.9 kPa/300 K: rho_i = 56.297, rho_f = 0.6877 -> 556.09 kg."""
    r = vented_mass(10.0, 7.0e6, 300.0, 98900.0, 300.0, KS07)
    assert r.gas_mass_kg == pytest.approx(556.09, abs=0.5)
    assert r.ch4_mass_kg == pytest.approx(r.gas_mass_kg * ch4_mass_fraction(KS07), rel=1e-12)


def test_no_pressure_drop_vents_nothing() -> None:
    """Equal pressures and temperatures vent zero mass."""
    assert vented_mass(10.0, 5.0e6, 300.0, 5.0e6, 300.0, KS07).gas_mass_kg == pytest.approx(0.0)


def test_invalid_inputs() -> None:
    """Pressure increase and non-positive volume are rejected."""
    with pytest.raises(ValueError, match="p_final_pa"):
        vented_mass(10.0, 1.0e6, 300.0, 2.0e6, 300.0, KS07)
    with pytest.raises(ValueError, match="volume_m3"):
        vented_mass(0.0, 7.0e6, 300.0, 98900.0, 300.0, KS07)
```

## Steps
- [x] Tests → FAIL → implement → full checks green.
- [x] **Docs.** ENGINEERING.md → "Flare" (equation, DE default and its source, unlit case) and "Blowdown" (equation, real-gas density, where the isolated volume comes from in S4). Work-log; `STATUS.md` (last 2.10, next 2.11).
- [ ] **Commit** `feat(engineering): add flare slip and blowdown vented mass`.
