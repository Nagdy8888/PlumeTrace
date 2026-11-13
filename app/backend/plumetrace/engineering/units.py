"""Unit conversions for the engineering core.

SI units inside; these helpers convert at the edges. Gas concentrations use the ideal gas law.
"""

from typing import Literal

import numpy as np
import numpy.typing as npt

from plumetrace.engineering.constants import (
    FT3_TO_M3,
    GWP20_CH4_FOSSIL,
    GWP100_CH4_FOSSIL,
    HOURS_PER_YEAR,
    M_CH4_KG_MOL,
    R_J_MOL_K,
)

FloatOrArray = float | npt.NDArray[np.float64]

_SECONDS_PER_HOUR = 3600.0
_PPM = 1e6


def kg_h_to_kg_s(rate_kg_h: float) -> float:
    """Convert a mass rate from kg/h to kg/s.

    Args:
        rate_kg_h: Mass rate in kg/h.

    Returns:
        Mass rate in kg/s (``rate_kg_h / 3600``).
    """
    return rate_kg_h / _SECONDS_PER_HOUR


def kg_s_to_kg_h(rate_kg_s: float) -> float:
    """Convert a mass rate from kg/s to kg/h.

    Args:
        rate_kg_s: Mass rate in kg/s.

    Returns:
        Mass rate in kg/h (``rate_kg_s * 3600``).
    """
    return rate_kg_s * _SECONDS_PER_HOUR


def kg_m3_to_ppm(
    conc_kg_m3: FloatOrArray,
    temp_k: float,
    pressure_pa: float,
    molar_mass_kg_mol: float = M_CH4_KG_MOL,
) -> FloatOrArray:
    """Convert a mass concentration to a mole fraction in ppm (ideal gas).

    Args:
        conc_kg_m3: Mass concentration in kg/m3 (scalar or array).
        temp_k: Air temperature in K.
        pressure_pa: Air pressure in Pa.
        molar_mass_kg_mol: Molar mass of the gas in kg/mol (default methane).

    Returns:
        Mole fraction in ppm, ``conc * R * T / (P * M) * 1e6``; same shape as the input.
    """
    return conc_kg_m3 * R_J_MOL_K * temp_k / (pressure_pa * molar_mass_kg_mol) * _PPM


def ppm_to_kg_m3(
    conc_ppm: FloatOrArray,
    temp_k: float,
    pressure_pa: float,
    molar_mass_kg_mol: float = M_CH4_KG_MOL,
) -> FloatOrArray:
    """Convert a mole fraction in ppm to a mass concentration (ideal gas).

    Args:
        conc_ppm: Mole fraction in ppm (scalar or array).
        temp_k: Air temperature in K.
        pressure_pa: Air pressure in Pa.
        molar_mass_kg_mol: Molar mass of the gas in kg/mol (default methane).

    Returns:
        Mass concentration in kg/m3, ``conc_ppm * 1e-6 * P * M / (R * T)``; same shape as the input.
    """
    return conc_ppm / _PPM * pressure_pa * molar_mass_kg_mol / (R_J_MOL_K * temp_k)


def scf_to_sm3(volume_scf: float) -> float:
    """Convert standard cubic feet to cubic metres.

    The 60 °F (scf) versus 15 °C (Sm3) reference difference, about 0.2 %, is ignored.

    Args:
        volume_scf: Volume in standard cubic feet.

    Returns:
        Volume in m3 (``volume_scf * 0.028316846592``).
    """
    return volume_scf * FT3_TO_M3


def kg_h_to_t_yr(rate_kg_h: float) -> float:
    """Convert a mass rate from kg/h to tonnes per year (8760 h year).

    Args:
        rate_kg_h: Mass rate in kg/h.

    Returns:
        Mass rate in t/yr (``rate_kg_h * 8760 / 1000``).
    """
    return rate_kg_h * HOURS_PER_YEAR / 1000.0


def co2e_kg(ch4_kg: float, horizon: Literal["GWP100", "GWP20"]) -> float:
    """Convert a methane mass to CO2-equivalent (IPCC AR6, fossil methane).

    Args:
        ch4_kg: Methane mass in kg.
        horizon: ``"GWP100"`` (29.8) or ``"GWP20"`` (82.5).

    Returns:
        CO2-equivalent mass in kg.
    """
    factor = GWP100_CH4_FOSSIL if horizon == "GWP100" else GWP20_CH4_FOSSIL
    return ch4_kg * factor
