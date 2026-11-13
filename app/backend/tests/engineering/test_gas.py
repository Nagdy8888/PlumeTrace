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
    mole_fractions={
        "CH4": 0.930,
        "C2H6": 0.035,
        "C3H8": 0.008,
        "nC4H10": 0.002,
        "CO2": 0.010,
        "N2": 0.015,
    }
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
    """Density rho = P*M/(Z*R*T) = 7e6*0.0173018/(0.86248*8.314462618*300) = 56.297 kg/m3."""
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
