"""Tests for blowdown vented mass (KS-07 gas; hand calculation in the docstring)."""

import pytest

from plumetrace.engineering.blowdown import vented_mass
from plumetrace.engineering.gas import GasComposition, ch4_mass_fraction

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
