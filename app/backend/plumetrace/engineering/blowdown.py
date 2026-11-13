"""Blowdown vented mass: gas released when an isolated volume is depressurised.

Pure function in SI units. The mass is the difference of the real-gas contents (density from
the Papay Z factor in `gas.py`) before and after.
"""

import math

from pydantic import BaseModel, ConfigDict

from plumetrace.engineering.gas import GasComposition, ch4_mass_fraction, density_kg_m3


class BlowdownResult(BaseModel):
    """Mass released by one blowdown."""

    model_config = ConfigDict(frozen=True)

    gas_mass_kg: float
    ch4_mass_kg: float


def _require_positive(name: str, value: float) -> None:
    """Raise ValueError unless value is finite and above zero."""
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and > 0, got {value}")


def _check_inputs(
    volume_m3: float,
    p_initial_pa: float,
    t_initial_k: float,
    p_final_pa: float,
    t_final_k: float,
) -> None:
    """Validate the blowdown inputs; raises ValueError with the offending name."""
    if not math.isfinite(volume_m3):
        raise ValueError(f"volume_m3 must be finite, got {volume_m3}")
    if volume_m3 <= 0.0:
        raise ValueError("volume_m3 must be > 0")
    _require_positive("p_initial_pa", p_initial_pa)
    _require_positive("t_initial_k", t_initial_k)
    _require_positive("p_final_pa", p_final_pa)
    _require_positive("t_final_k", t_final_k)
    if p_final_pa > p_initial_pa:
        raise ValueError("p_final_pa must not exceed p_initial_pa")


def _density_or_raise(name: str, pressure_pa: float, temp_k: float, comp: GasComposition) -> float:
    """Return the real-gas density, or raise if Z is not positive (outside Papay's range)."""
    rho_kg_m3 = density_kg_m3(pressure_pa, temp_k, comp)
    if not math.isfinite(rho_kg_m3) or rho_kg_m3 <= 0.0:
        raise ValueError(
            f"{name} density is not positive ({rho_kg_m3}): outside the range of the Z correlation"
        )
    return rho_kg_m3


def vented_mass(
    volume_m3: float,
    p_initial_pa: float,
    t_initial_k: float,
    p_final_pa: float,
    t_final_k: float,
    comp: GasComposition,
) -> BlowdownResult:
    """Return the gas and methane mass released by a blowdown of an isolated volume.

    ``gas = V * (rho(p_i, T_i) - rho(p_f, T_f))``; ``ch4 = gas * ch4_mass_fraction(comp)``.
    Pressures are absolute.

    Args:
        volume_m3: Isolated volume in m3 (finite, above zero).
        p_initial_pa: Absolute pressure before the blowdown in Pa.
        t_initial_k: Gas temperature before the blowdown in K.
        p_final_pa: Absolute pressure after the blowdown in Pa (not above ``p_initial_pa``).
        t_final_k: Gas temperature after the blowdown in K.
        comp: Gas composition.

    Returns:
        Released gas mass and methane mass in kg.

    Raises:
        ValueError: If an input is not finite or not above zero, the pressure rises, a density
            is not positive (Z correlation out of range), the final gas is denser than the
            initial gas (nothing vented) or the mass overflows.
    """
    _check_inputs(volume_m3, p_initial_pa, t_initial_k, p_final_pa, t_final_k)
    rho_i_kg_m3 = _density_or_raise("initial", p_initial_pa, t_initial_k, comp)
    rho_f_kg_m3 = _density_or_raise("final", p_final_pa, t_final_k, comp)
    if rho_f_kg_m3 > rho_i_kg_m3:
        raise ValueError("final gas is denser than the initial gas: nothing is vented")
    gas_mass_kg = volume_m3 * (rho_i_kg_m3 - rho_f_kg_m3)
    if not math.isfinite(gas_mass_kg):
        raise ValueError("vented mass overflows: volume_m3 is too large")
    return BlowdownResult(
        gas_mass_kg=gas_mass_kg, ch4_mass_kg=gas_mass_kg * ch4_mass_fraction(comp)
    )
