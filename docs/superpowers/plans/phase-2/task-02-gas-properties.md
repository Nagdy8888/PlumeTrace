# Phase 2 · Task 2 — Gas properties (composition, Z factor, density, fractions)

**Skills:** `plan-execution`, `engineering-core`, `project-documentation`.

## Files
| Action | Path |
|---|---|
| Modify | `app/backend/plumetrace/engineering/constants.py` (add the component table) |
| Create | `app/backend/plumetrace/engineering/gas.py`, `app/backend/tests/engineering/test_gas.py` |

## Interface

Add to `constants.py`:
```python
@dataclass(frozen=True)
class ComponentProperties:
    molar_mass_kg_mol: float
    critical_temp_k: float
    critical_pressure_pa: float

# source: NIST Chemistry WebBook (molar masses, critical constants), retrieved 2026-11.
GAS_COMPONENTS: Final[Mapping[str, ComponentProperties]] = MappingProxyType({
    "CH4":    ComponentProperties(0.016043, 190.56, 4.599e6),
    "C2H6":   ComponentProperties(0.03007,  305.32, 4.872e6),
    "C3H8":   ComponentProperties(0.044097, 369.83, 4.248e6),
    "nC4H10": ComponentProperties(0.05812,  425.12, 3.796e6),
    "CO2":    ComponentProperties(0.04401,  304.13, 7.377e6),
    "N2":     ComponentProperties(0.028013, 126.2,  3.396e6),
})
HYDROCARBONS: Final[frozenset[str]] = frozenset({"CH4", "C2H6", "C3H8", "nC4H10"})
```

`gas.py`:
- `class GasComposition(BaseModel)` (`frozen=True`): `mole_fractions: dict[str, float]`. Validator: every key in `GAS_COMPONENTS` (else `f"unknown gas component {key}"`); every value ≥ 0; `abs(sum − 1) ≤ 1e-6` (else `f"mole fractions sum to {total:.6f}, expected 1"`).
- `def molar_mass_kg_mol(comp: GasComposition) -> float` — Σ xᵢ·Mᵢ
- `def pseudo_critical(comp: GasComposition) -> tuple[float, float]` — Kay's mixing rule, returns `(tpc_k, ppc_pa)`
- `def z_factor_papay(pressure_pa: float, temp_k: float, comp: GasComposition) -> float` — `Pr = P/Ppc`, `Tr = T/Tpc`, `Z = 1 − 3.52·Pr·exp(−2.260·Tr) + 0.247·Pr²·exp(−1.878·Tr)` (Papay 1968; docstring: valid for sweet natural gas at moderate reduced pressures)
- `def density_kg_m3(pressure_pa: float, temp_k: float, comp: GasComposition) -> float` — `P·M/(Z·R·T)`
- `def ch4_mass_fraction(comp: GasComposition) -> float` — `x_CH4·M_CH4 / M_mix` (whole gas)
- `def ch4_hydrocarbon_mass_fraction(comp: GasComposition) -> float` — `x_CH4·M_CH4 / Σ_{HYDROCARBONS} xᵢ·Mᵢ` (used to convert total-organic-compound factors to CH4)
- `def ch4_hydrocarbon_mole_fraction(comp: GasComposition) -> float` — `x_CH4 / Σ_{HYDROCARBONS} xᵢ` (used to convert total-hydrocarbon volumes to CH4)
- `def std_volume_to_ch4_kg(volume_sm3: float, comp: GasComposition) -> float` — `(P_STD·V/(R·T_STD))·x_CH4·M_CH4`

## Tests (full code) — `app/backend/tests/engineering/test_gas.py`
```python
"""Tests for gas properties using the KS-07 composition (hand calculations in docstrings)."""

import pytest
from pydantic import ValidationError

from plumetrace.engineering.gas import (
    GasComposition,
    ch4_hydrocarbon_mass_fraction,
    ch4_hydrocarbon_mole_fraction,
    ch4_mass_fraction,
    density_kg_m3,
    molar_mass_kg_mol,
    pseudo_critical,
    std_volume_to_ch4_kg,
    z_factor_papay,
)

KS07 = GasComposition(
    mole_fractions={"CH4": 0.930, "C2H6": 0.035, "C3H8": 0.008, "nC4H10": 0.002,
                    "CO2": 0.010, "N2": 0.015}
)


def test_molar_mass() -> None:
    """Sum x_i*M_i = 14.920+1.052+0.353+0.116+0.440+0.420 g/mol = 17.302 g/mol."""
    assert molar_mass_kg_mol(KS07) == pytest.approx(0.0173018, abs=2e-6)


def test_pseudo_critical_kay_rule() -> None:
    """Kay's rule: Tpc = 196.65 K, Ppc = 4.6139 MPa."""
    tpc, ppc = pseudo_critical(KS07)
    assert tpc == pytest.approx(196.650, abs=0.01)
    assert ppc == pytest.approx(4.613876e6, abs=10.0)


def test_papay_z_at_station_discharge() -> None:
    """Papay (1968) at 7.0 MPa, 300 K: Tr = 1.5255, Pr = 1.5172 -> Z = 0.86248."""
    assert z_factor_papay(7.0e6, 300.0, KS07) == pytest.approx(0.86248, abs=5e-4)


def test_papay_z_near_ideal_at_standard_conditions() -> None:
    """At 101325 Pa, 288.15 K the gas is nearly ideal (Z = 0.99719)."""
    assert z_factor_papay(101325.0, 288.15, KS07) == pytest.approx(0.99719, abs=5e-4)


def test_density_at_discharge() -> None:
    """rho = P*M/(Z*R*T) = 7e6*0.0173018/(0.86248*8.314462618*300) = 56.297 kg/m3."""
    assert density_kg_m3(7.0e6, 300.0, KS07) == pytest.approx(56.297, abs=0.05)


def test_methane_fractions() -> None:
    """Whole-gas CH4 mass fraction 0.86234; of hydrocarbon mass 0.90746; of HC moles 0.95385."""
    assert ch4_mass_fraction(KS07) == pytest.approx(0.86234, abs=2e-4)
    assert ch4_hydrocarbon_mass_fraction(KS07) == pytest.approx(0.90746, abs=2e-4)
    assert ch4_hydrocarbon_mole_fraction(KS07) == pytest.approx(0.930 / 0.975, abs=1e-9)


def test_std_volume_to_ch4_mass() -> None:
    """1 Sm3 holds P/(R*T) = 42.2925 mol; CH4 = 42.2925*0.930*0.016043 kg = 0.63101 kg."""
    assert std_volume_to_ch4_kg(1.0, KS07) == pytest.approx(0.63101, abs=2e-4)


def test_composition_must_sum_to_one() -> None:
    """A composition summing to 0.99 is rejected, naming the sum."""
    with pytest.raises(ValidationError, match="0.99"):
        GasComposition(mole_fractions={"CH4": 0.94, "N2": 0.05})


def test_unknown_component_rejected() -> None:
    """Unknown species are rejected by name."""
    with pytest.raises(ValidationError, match="H2S"):
        GasComposition(mole_fractions={"CH4": 0.99, "H2S": 0.01})
```

## Steps
- [x] **1.** Write the test → fails (import error). **2.** Add the constants and implement `gas.py`.
- [x] **3.** Full checks green.
- [x] **4. Docs.** ENGINEERING.md → "Gas properties": component table with sources, Kay's rule, Papay equation and validity, the three CH4 fractions and when each is used. Work-log; `STATUS.md` (last 2.2, next 2.3).
- [ ] **5. Commit** `feat(engineering): add gas composition, Papay Z factor and density`.
