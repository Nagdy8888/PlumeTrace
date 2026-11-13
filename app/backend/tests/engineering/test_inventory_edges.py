"""Edge cases of the inventory: bad counts, bad gas, unknown names, huge input, table integrity."""

import math
from typing import Any

import pytest

from plumetrace.engineering.constants import (
    FT3_TO_M3,
    M_CH4_KG_MOL,
    P_STD_PA,
    R_J_MOL_K,
    T_STD_K,
)
from plumetrace.engineering.emission_factors import (
    EPA_1995_AVERAGE_GAS_TOC_KG_H,
    SUBPART_W_W4_LEAKER_THC_SCF_H,
)
from plumetrace.engineering.gas import GasComposition
from plumetrace.engineering.inventory import bottom_up_ch4_kg_h, leaker_ch4_kg_h

KS07 = GasComposition(
    mole_fractions={
        "CH4": 0.930,
        "C2H6": 0.035,
        "C3H8": 0.008,
        "nC4H10": 0.002,
        "CO2": 0.010,
        "N2": 0.015,
    }
)
NO_HYDROCARBON = GasComposition(mole_fractions={"CO2": 0.4, "N2": 0.6})
NO_METHANE = GasComposition(mole_fractions={"C2H6": 0.9, "N2": 0.1})
LEAN = GasComposition(mole_fractions={"CH4": 0.99, "N2": 0.01})
COMPRESSOR = {"valves": 73, "connectors": 179, "open_ended_lines": 3, "pressure_relief_valves": 4}
LEAKER_COMPONENTS = [
    "valve",
    "connector",
    "open_ended_line",
    "pressure_relief_valve",
    "meter",
    "other",
]
KS07_CH4_HC_MASS = (
    0.930 * 16.043 / (0.930 * 16.043 + 0.035 * 30.07 + 0.008 * 44.097 + 0.002 * 58.12)
)


def _counts(**changes: object) -> Any:
    """Return the compressor counts with some entries replaced."""
    return {**COMPRESSOR, **changes}


def test_no_equipment_emits_zero() -> None:
    """An empty site has no component emissions."""
    assert bottom_up_ch4_kg_h({}, KS07) == 0.0


def test_pressure_relief_valves_use_the_others_factor() -> None:
    """4 relief valves x 8.8e-3 kg TOC/h x CH4 share of hydrocarbon mass, from raw numbers."""
    only_prv = {"valves": 0, "connectors": 0, "open_ended_lines": 0, "pressure_relief_valves": 4}
    expected = 4 * 8.8e-3 * KS07_CH4_HC_MASS
    assert bottom_up_ch4_kg_h({"V": only_prv}, KS07) == pytest.approx(expected, rel=1e-12)


def test_linear_in_counts() -> None:
    """Doubling every count doubles the inventory."""
    double = {k: 2 * v for k, v in COMPRESSOR.items()}
    one = bottom_up_ch4_kg_h({"A": COMPRESSOR}, KS07)
    assert bottom_up_ch4_kg_h({"A": double}, KS07) == pytest.approx(2.0 * one, rel=1e-12)


def test_leaner_gas_gives_more_methane_for_the_same_components() -> None:
    """Less ethane and heavier gas means a larger methane share of the total organics."""
    assert bottom_up_ch4_kg_h({"A": COMPRESSOR}, LEAN) > bottom_up_ch4_kg_h({"A": COMPRESSOR}, KS07)


def test_gas_without_methane_gives_zero_not_error() -> None:
    """A hydrocarbon gas with no methane emits zero methane (a valid, if odd, input)."""
    assert bottom_up_ch4_kg_h({"A": COMPRESSOR}, NO_METHANE) == 0.0
    assert leaker_ch4_kg_h("valve", "compressor", NO_METHANE) == 0.0


@pytest.mark.parametrize("bad", [-1, 1.5, float("nan"), None, "3"])
def test_bad_count_value_is_value_error(bad: object) -> None:
    """A negative, fractional, NaN, missing or text count is rejected, naming the field."""
    with pytest.raises(ValueError, match="valves"):
        bottom_up_ch4_kg_h({"K-201": _counts(valves=bad)}, KS07)


def test_missing_count_key_is_value_error() -> None:
    """A counts entry without one of the four keys is rejected, naming the tag and key."""
    partial: Any = {k: v for k, v in COMPRESSOR.items() if k != "connectors"}
    with pytest.raises(ValueError, match="K-201.*connectors"):
        bottom_up_ch4_kg_h({"K-201": partial}, KS07)


def test_error_names_the_tag() -> None:
    """The tag of the offending equipment is in the message."""
    site: Any = {"K-201": COMPRESSOR, "K-999": _counts(connectors=-4)}
    with pytest.raises(ValueError, match="K-999"):
        bottom_up_ch4_kg_h(site, KS07)


def test_absurd_count_is_value_error_not_overflow() -> None:
    """An integer too large for a float raises ValueError, not OverflowError or inf."""
    with pytest.raises(ValueError, match="finite"):
        bottom_up_ch4_kg_h({"A": _counts(valves=10**400)}, KS07)


def test_large_site_is_finite() -> None:
    """A million valves is a big but finite number."""
    out = bottom_up_ch4_kg_h({"A": _counts(valves=10**6)}, KS07)
    assert math.isfinite(out)
    toc_kg_h = 10**6 * 4.5e-3 + 179 * 2.0e-4 + 3 * 2.0e-3 + 4 * 8.8e-3
    assert out == pytest.approx(toc_kg_h * KS07_CH4_HC_MASS, rel=1e-12)


def test_gas_without_hydrocarbons_is_value_error() -> None:
    """A TOC or THC factor cannot be converted to methane without any hydrocarbon in the gas."""
    with pytest.raises(ValueError, match="hydrocarbon"):
        bottom_up_ch4_kg_h({"A": COMPRESSOR}, NO_HYDROCARBON)
    with pytest.raises(ValueError, match="hydrocarbon"):
        leaker_ch4_kg_h("valve", "compressor", NO_HYDROCARBON)


@pytest.mark.parametrize("location", ["compressor", "non_compressor"])
@pytest.mark.parametrize("component", LEAKER_COMPONENTS)
def test_every_leaker_factor_is_positive_and_finite(component: Any, location: Any) -> None:
    """All twelve W-4 cells convert to a positive finite methane rate."""
    out = leaker_ch4_kg_h(component, location, KS07)
    assert math.isfinite(out)
    assert out > 0.0


def test_leaker_meter_from_raw_numbers() -> None:
    """4.79 scf THC/h (non-compressor meter) converted step by step from the raw constants."""
    mol_per_m3 = P_STD_PA / (R_J_MOL_K * T_STD_K)
    expected = 4.79 * FT3_TO_M3 * mol_per_m3 * (0.930 / 0.975) * M_CH4_KG_MOL
    assert leaker_ch4_kg_h("meter", "non_compressor", KS07) == pytest.approx(expected, rel=1e-12)


def test_leaker_scales_with_methane_share() -> None:
    """A leaner gas (higher methane share of hydrocarbons) gives a larger methane rate."""
    lean = leaker_ch4_kg_h("valve", "compressor", LEAN)
    assert lean > leaker_ch4_kg_h("valve", "compressor", KS07)


@pytest.mark.parametrize(
    ("component", "location"),
    [("flange", "compressor"), ("", "compressor"), ("valve", "pipeline"), ("valve", "")],
)
def test_unknown_leaker_name_is_value_error(component: Any, location: Any) -> None:
    """An unknown component or location is a ValueError that names it, not a KeyError."""
    with pytest.raises(ValueError, match="unknown"):
        leaker_ch4_kg_h(component, location, KS07)


def test_factor_tables_are_complete_and_read_only() -> None:
    """Both W-4 locations carry the same six components; the tables cannot be mutated."""
    w4 = SUBPART_W_W4_LEAKER_THC_SCF_H
    epa: Any = EPA_1995_AVERAGE_GAS_TOC_KG_H
    w4_compressor: Any = w4["compressor"]
    assert set(w4) == {"compressor", "non_compressor"}
    assert set(w4["compressor"]) == set(w4["non_compressor"]) == set(LEAKER_COMPONENTS)
    assert set(EPA_1995_AVERAGE_GAS_TOC_KG_H) == {
        "valves",
        "pump_seals",
        "others",
        "connectors",
        "flanges",
        "open_ended_lines",
    }
    with pytest.raises(TypeError):
        epa["valves"] = 0.0
    with pytest.raises(TypeError):
        w4_compressor["valve"] = 0.0
