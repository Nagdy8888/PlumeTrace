# Phase 2 · Task 11 — Emission-factor inventory and methane intensity

**Skills:** `plan-execution`, `engineering-core`, `project-documentation`.

The factor values below were read by the planner directly from the cited documents on 2026-11-12
(EPA-453/R-95-017 PDF; 40 CFR 98 Subpart W, CFR 2025 edition via govinfo). Copy them verbatim.

## Files
Create `app/backend/plumetrace/engineering/emission_factors.py`, `inventory.py`, `intensity.py`, and tests `app/backend/tests/engineering/test_inventory.py`, `test_intensity.py`.

## Interface

`emission_factors.py` (constants only, `Final`, `MappingProxyType`; each with a source comment):
```python
# source: EPA-453/R-95-017 "1995 Protocol for Equipment Leak Emission Estimates", Table 2-4
# "Oil and Gas Production Operations Average Emission Factors", gas service, p. 2-14.
# kg/h/source of TOTAL ORGANIC COMPOUNDS (includes methane and ethane). "others" covers
# compressors, diaphragms, drains, dump arms, hatches, instruments, meters, pressure relief
# valves, polished rods, relief valves and vents (table footnote c).
EPA_1995_AVERAGE_GAS_TOC_KG_H = MappingProxyType({
    "valves": 4.5e-3, "pump_seals": 2.4e-3, "others": 8.8e-3,
    "connectors": 2.0e-4, "flanges": 3.9e-4, "open_ended_lines": 2.0e-3,
})

# source: 40 CFR Part 98 Subpart W, Table W-4 "Default Total Hydrocarbon Leaker Emission
# Factors", onshore natural gas transmission compression, gas service, column "If you survey
# using any of the methods in § 98.234(a)(1), (3), or (5)" (optical gas imaging);
# [89 FR 42325, May 14, 2024]; CFR 2025 edition. Units: scf total hydrocarbon / hour / component.
SUBPART_W_W4_LEAKER_THC_SCF_H = MappingProxyType({
    "compressor": MappingProxyType({
        "valve": 24.2, "connector": 9.13, "open_ended_line": 28.2,
        "pressure_relief_valve": 64.8, "meter": 31.6, "other": 6.70,
    }),
    "non_compressor": MappingProxyType({
        "valve": 10.5, "connector": 9.3, "open_ended_line": 18.4,
        "pressure_relief_valve": 3.28, "meter": 4.79, "other": 6.70,
    }),
})
```

`inventory.py`:
- `class ComponentCountsDict(TypedDict)`: `valves: int`, `connectors: int`, `open_ended_lines: int`, `pressure_relief_valves: int` (callers pass `ComponentCounts.model_dump()` from the facility package — engineering never imports facility).
- `LeakerComponent = Literal["valve", "connector", "open_ended_line", "pressure_relief_valve", "meter", "other"]`; `LeakerLocation = Literal["compressor", "non_compressor"]`
- `def bottom_up_ch4_kg_h(counts: Mapping[str, ComponentCountsDict], comp: GasComposition) -> float` — `Σ_tags (valves·f["valves"] + connectors·f["connectors"] + open_ended_lines·f["open_ended_lines"] + pressure_relief_valves·f["others"]) × ch4_hydrocarbon_mass_fraction(comp)` with `f = EPA_1995_AVERAGE_GAS_TOC_KG_H` (docstring: TOC→CH4 by the methane share of hydrocarbon mass — an approximation; pressure relief valves use the "others" factor per the table footnote).
- `def leaker_ch4_kg_h(component: LeakerComponent, location: LeakerLocation, comp: GasComposition) -> float` — `scf_h × FT3_TO_M3 × (P_STD_PA/(R_J_MOL_K·T_STD_K)) × ch4_hydrocarbon_mole_fraction(comp) × M_CH4_KG_MOL` (docstring: the 60 °F scf vs 15 °C Sm³ reference difference is ignored, ~0.2 %).

`intensity.py`:
- `def methane_intensity_percent(ch4_emitted_kg_h: float, throughput_sm3_h: float) -> float` — emitted CH4 volume at standard conditions (`ch4_emitted_kg_h / ppm_to_kg_m3(1e6, T_STD_K, P_STD_PA)`) divided by gas throughput (Sm³/h) × 100. Docstring: volume basis, following the OGCI methane-intensity methodology (methane emitted volume ÷ gas handled volume). `ValueError` if `throughput_sm3_h ≤ 0`.

## Tests (full code)

`app/backend/tests/engineering/test_inventory.py`:
```python
"""Tests for the emission-factor inventory and leaker factors (hand calculations)."""

import pytest

from plumetrace.engineering.emission_factors import (
    EPA_1995_AVERAGE_GAS_TOC_KG_H,
    SUBPART_W_W4_LEAKER_THC_SCF_H,
)
from plumetrace.engineering.gas import GasComposition
from plumetrace.engineering.inventory import bottom_up_ch4_kg_h, leaker_ch4_kg_h

KS07 = GasComposition(
    mole_fractions={"CH4": 0.930, "C2H6": 0.035, "C3H8": 0.008, "nC4H10": 0.002,
                    "CO2": 0.010, "N2": 0.015}
)
COMPRESSOR = {"valves": 73, "connectors": 179, "open_ended_lines": 3, "pressure_relief_valves": 4}


def test_factor_tables_match_sources() -> None:
    """Spot-check transcribed values against EPA-453/R-95-017 Table 2-4 and Subpart W Table W-4."""
    assert EPA_1995_AVERAGE_GAS_TOC_KG_H["valves"] == 4.5e-3
    assert EPA_1995_AVERAGE_GAS_TOC_KG_H["others"] == 8.8e-3
    assert SUBPART_W_W4_LEAKER_THC_SCF_H["non_compressor"]["valve"] == 10.5
    assert SUBPART_W_W4_LEAKER_THC_SCF_H["compressor"]["pressure_relief_valve"] == 64.8


def test_bottom_up_one_compressor() -> None:
    """73*4.5e-3 + 179*2.0e-4 + 3*2.0e-3 + 4*8.8e-3 = 0.4055 kg TOC/h; x 0.90746 = 0.36798 kg CH4/h."""
    assert bottom_up_ch4_kg_h({"K-201": COMPRESSOR}, KS07) == pytest.approx(0.36798, abs=2e-5)


def test_bottom_up_sums_equipment() -> None:
    """Two identical units emit twice as much; zero counts add nothing."""
    zeros = {"valves": 0, "connectors": 0, "open_ended_lines": 0, "pressure_relief_valves": 0}
    one = bottom_up_ch4_kg_h({"K-201": COMPRESSOR}, KS07)
    two = bottom_up_ch4_kg_h({"K-201": COMPRESSOR, "K-202": COMPRESSOR, "VS-250": zeros}, KS07)
    assert two == pytest.approx(2.0 * one)


def test_leaker_valve_conversion() -> None:
    """10.5 scf THC/h -> 0.29733 m3/h * 42.2925 mol/m3 * (0.930/0.975) * 0.016043 = 0.19243 kg/h."""
    assert leaker_ch4_kg_h("valve", "non_compressor", KS07) == pytest.approx(0.19243, abs=2e-5)
    assert leaker_ch4_kg_h("valve", "compressor", KS07) == pytest.approx(0.44349, abs=2e-5)
```

`app/backend/tests/engineering/test_intensity.py`:
```python
"""Tests for methane intensity (volume basis)."""

import pytest

from plumetrace.engineering.intensity import methane_intensity_percent


def test_one_percent() -> None:
    """6.785 kg/h CH4 = 10.000 Sm3/h (rho 0.6785 kg/Sm3); / 1000 Sm3/h throughput = 1.000 %."""
    assert methane_intensity_percent(6.785, 1000.0) == pytest.approx(1.0, rel=1e-3)


def test_zero_throughput_rejected() -> None:
    """Intensity is undefined without throughput."""
    with pytest.raises(ValueError):
        methane_intensity_percent(1.0, 0.0)
```

## Steps
- [x] Tests → FAIL → implement → full checks green.
- [x] **Docs.** ENGINEERING.md → "Inventory" (both factor tables with full citations, TOC→CH4 and THC→CH4 conversions, which factor serves which job: average for the site inventory, W-4 leaker for an OGI-found leak in S6) and "Methane intensity" (definition, basis, citation). Work-log; `STATUS.md` (last 2.11, next 2.12).
- [ ] **Commit** `feat(engineering): add emission-factor inventory and methane intensity`.
