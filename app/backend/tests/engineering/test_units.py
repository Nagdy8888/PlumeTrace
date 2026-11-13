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
    """Round trip ppm -> kg/m3 -> ppm returns the input."""
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
