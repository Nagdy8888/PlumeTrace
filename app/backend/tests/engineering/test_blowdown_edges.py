"""Edge cases of blowdown: bad volume, pressure or temperature, contraction, overflow."""

import math

import pytest

from plumetrace.engineering.blowdown import BlowdownResult, vented_mass
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
NAN = float("nan")
INF = float("inf")


def test_result_is_frozen() -> None:
    """BlowdownResult cannot be changed after creation."""
    r = vented_mass(10.0, 7.0e6, 300.0, 98900.0, 300.0, KS07)
    assert isinstance(r, BlowdownResult)
    with pytest.raises(ValueError):
        r.gas_mass_kg = 1.0


def test_mass_is_linear_in_volume_and_ch4_is_a_fraction_of_gas() -> None:
    """Doubling the volume doubles the vented mass; methane is the KS-07 mass fraction."""
    a = vented_mass(5.0, 7.0e6, 300.0, 98900.0, 300.0, KS07)
    b = vented_mass(10.0, 7.0e6, 300.0, 98900.0, 300.0, KS07)
    assert b.gas_mass_kg == pytest.approx(2 * a.gas_mass_kg, rel=1e-12)
    assert 0.0 < b.ch4_mass_kg < b.gas_mass_kg
    assert b.ch4_mass_kg == pytest.approx(b.gas_mass_kg * ch4_mass_fraction(KS07), rel=1e-12)


def test_deeper_blowdown_vents_more() -> None:
    """Dropping to a lower final pressure vents more mass than stopping at a higher one."""
    to_low = vented_mass(10.0, 7.0e6, 300.0, 1.0e5, 300.0, KS07).gas_mass_kg
    to_mid = vented_mass(10.0, 7.0e6, 300.0, 1.0e6, 300.0, KS07).gas_mass_kg
    assert to_low > to_mid > 0.0


def test_cold_final_gas_at_lower_pressure_still_vents() -> None:
    """A real blowdown cools the gas; a pressure drop with a colder final state still vents."""
    r = vented_mass(10.0, 7.0e6, 300.0, 2.0e6, 250.0, KS07)
    assert r.gas_mass_kg > 0.0
    assert math.isfinite(r.ch4_mass_kg)


def test_final_state_denser_than_initial_is_value_error() -> None:
    """Same pressure but a colder final gas is denser: nothing is vented, so it is rejected."""
    with pytest.raises(ValueError, match="denser"):
        vented_mass(10.0, 5.0e6, 300.0, 5.0e6, 250.0, KS07)


@pytest.mark.parametrize("volume", [0.0, -1.0, -1e-9])
def test_non_positive_volume_message(volume: float) -> None:
    """The plan message is kept for zero and negative volume."""
    with pytest.raises(ValueError, match="volume_m3 must be > 0"):
        vented_mass(volume, 7.0e6, 300.0, 98900.0, 300.0, KS07)


@pytest.mark.parametrize("volume", [NAN, INF, -INF])
def test_non_finite_volume_is_value_error(volume: float) -> None:
    """NaN and infinite volume are rejected, not propagated."""
    with pytest.raises(ValueError, match="volume_m3"):
        vented_mass(volume, 7.0e6, 300.0, 98900.0, 300.0, KS07)


@pytest.mark.parametrize("bad", [0.0, -1.0, NAN, INF, -INF])
def test_bad_initial_state_is_value_error(bad: float) -> None:
    """Initial pressure and temperature must be finite and above zero."""
    with pytest.raises(ValueError, match="p_initial_pa"):
        vented_mass(10.0, bad, 300.0, 98900.0, 300.0, KS07)
    with pytest.raises(ValueError, match="t_initial_k"):
        vented_mass(10.0, 7.0e6, bad, 98900.0, 300.0, KS07)


@pytest.mark.parametrize("bad", [0.0, -1.0, NAN, INF, -INF])
def test_bad_final_state_is_value_error(bad: float) -> None:
    """Final pressure and temperature must be finite and above zero."""
    with pytest.raises(ValueError, match="p_final_pa"):
        vented_mass(10.0, 7.0e6, 300.0, bad, 300.0, KS07)
    with pytest.raises(ValueError, match="t_final_k"):
        vented_mass(10.0, 7.0e6, 300.0, 98900.0, bad, KS07)


def test_pressure_increase_keeps_plan_message() -> None:
    """A final pressure above the initial one raises the plan message."""
    with pytest.raises(ValueError, match="p_final_pa must not exceed p_initial_pa"):
        vented_mass(10.0, 1.0e6, 300.0, 2.0e6, 300.0, KS07)


def test_density_outside_correlation_range_is_value_error() -> None:
    """At 20 K and 10 MPa Papay Z is negative (far outside its range): rejected, not used."""
    with pytest.raises(ValueError, match="density"):
        vented_mass(10.0, 1.0e7, 20.0, 1.0e5, 20.0, KS07)


def test_overflowing_mass_is_value_error() -> None:
    """A volume so large the mass overflows to infinity is rejected, never returned."""
    with pytest.raises(ValueError, match="overflow"):
        vented_mass(1.0e308, 7.0e6, 300.0, 98900.0, 300.0, KS07)


def test_tiny_volume_gives_tiny_finite_mass() -> None:
    """A microscopic volume gives a proportionally tiny, finite mass."""
    r = vented_mass(1.0e-9, 7.0e6, 300.0, 98900.0, 300.0, KS07)
    assert 0.0 < r.gas_mass_kg < 1e-6
