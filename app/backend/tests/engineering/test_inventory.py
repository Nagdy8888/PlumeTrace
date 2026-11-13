"""Tests for the emission-factor inventory and leaker factors (hand calculations)."""

import pytest

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
COMPRESSOR = {"valves": 73, "connectors": 179, "open_ended_lines": 3, "pressure_relief_valves": 4}


def test_factor_tables_match_sources() -> None:
    """Spot-check transcribed values against EPA-453/R-95-017 Table 2-4 and Subpart W Table W-4."""
    assert EPA_1995_AVERAGE_GAS_TOC_KG_H["valves"] == 4.5e-3
    assert EPA_1995_AVERAGE_GAS_TOC_KG_H["others"] == 8.8e-3
    assert SUBPART_W_W4_LEAKER_THC_SCF_H["non_compressor"]["valve"] == 10.5
    assert SUBPART_W_W4_LEAKER_THC_SCF_H["compressor"]["pressure_relief_valve"] == 64.8


def test_bottom_up_one_compressor() -> None:
    """Hand calculation for one compressor.

    73*4.5e-3 + 179*2.0e-4 + 3*2.0e-3 + 4*8.8e-3 = 0.4055 kg TOC/h; x 0.90746 = 0.36798 kg CH4/h.
    """
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
