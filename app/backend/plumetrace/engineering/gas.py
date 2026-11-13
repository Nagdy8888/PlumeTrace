"""Gas properties: composition, pseudo-critical constants, Z factor, density, methane fractions.

Pure functions in SI units. Z uses the Papay (1968) correlation with Kay's mixing rule.
"""

import math

from pydantic import BaseModel, ConfigDict, model_validator

from plumetrace.engineering.constants import (
    GAS_COMPONENTS,
    HYDROCARBONS,
    M_CH4_KG_MOL,
    P_STD_PA,
    R_J_MOL_K,
    T_STD_K,
)


class GasComposition(BaseModel):
    """A gas mixture as mole fractions of the known components.

    Attributes:
        mole_fractions: Mole fraction per component name (keys of ``GAS_COMPONENTS``).
    """

    model_config = ConfigDict(frozen=True)

    mole_fractions: dict[str, float]

    @model_validator(mode="after")
    def _check_fractions(self) -> "GasComposition":
        """Reject unknown components, negative fractions and a sum other than 1.

        Raises:
            ValueError: If a key is unknown, a value is negative or the sum is not 1.
        """
        for key, value in self.mole_fractions.items():
            if key not in GAS_COMPONENTS:
                raise ValueError(f"unknown gas component {key}")
            if value < 0:
                raise ValueError(f"mole fraction of {key} is negative")
        total = sum(self.mole_fractions.values())
        if abs(total - 1) > 1e-6:
            raise ValueError(f"mole fractions sum to {total:.6f}, expected 1")
        return self


def molar_mass_kg_mol(comp: GasComposition) -> float:
    """Return the mixture molar mass, the sum of x_i * M_i.

    Args:
        comp: Gas composition.

    Returns:
        Molar mass in kg/mol.
    """
    return sum(x * GAS_COMPONENTS[k].molar_mass_kg_mol for k, x in comp.mole_fractions.items())


def pseudo_critical(comp: GasComposition) -> tuple[float, float]:
    """Return the pseudo-critical temperature and pressure by Kay's mixing rule.

    Args:
        comp: Gas composition.

    Returns:
        Tuple ``(tpc_k, ppc_pa)``, mole-fraction weighted critical constants.
    """
    tpc_k = sum(x * GAS_COMPONENTS[k].critical_temp_k for k, x in comp.mole_fractions.items())
    ppc_pa = sum(x * GAS_COMPONENTS[k].critical_pressure_pa for k, x in comp.mole_fractions.items())
    return tpc_k, ppc_pa


def z_factor_papay(pressure_pa: float, temp_k: float, comp: GasComposition) -> float:
    """Return the gas compressibility factor from the Papay (1968) correlation.

    Z = 1 - 3.52*Pr*exp(-2.260*Tr) + 0.247*Pr^2*exp(-1.878*Tr). Valid for sweet natural gas
    at moderate reduced pressures.

    Args:
        pressure_pa: Absolute pressure in Pa.
        temp_k: Temperature in K.
        comp: Gas composition.

    Returns:
        Compressibility factor Z (dimensionless).
    """
    tpc_k, ppc_pa = pseudo_critical(comp)
    pr = pressure_pa / ppc_pa
    tr = temp_k / tpc_k
    return 1 - 3.52 * pr * math.exp(-2.260 * tr) + 0.247 * pr**2 * math.exp(-1.878 * tr)


def density_kg_m3(pressure_pa: float, temp_k: float, comp: GasComposition) -> float:
    """Return the real-gas density P*M/(Z*R*T).

    Args:
        pressure_pa: Absolute pressure in Pa.
        temp_k: Temperature in K.
        comp: Gas composition.

    Returns:
        Density in kg/m3.
    """
    z = z_factor_papay(pressure_pa, temp_k, comp)
    return pressure_pa * molar_mass_kg_mol(comp) / (z * R_J_MOL_K * temp_k)


def ch4_mass_fraction(comp: GasComposition) -> float:
    """Return the CH4 mass fraction of the whole gas, x_CH4 * M_CH4 / M_mix.

    Args:
        comp: Gas composition.

    Returns:
        Mass fraction (dimensionless).
    """
    return comp.mole_fractions.get("CH4", 0.0) * M_CH4_KG_MOL / molar_mass_kg_mol(comp)


def ch4_hydrocarbon_mass_fraction(comp: GasComposition) -> float:
    """Return the CH4 share of hydrocarbon mass.

    Used to convert total-organic-compound factors to CH4.

    Args:
        comp: Gas composition.

    Returns:
        x_CH4 * M_CH4 divided by the sum of x_i * M_i over the hydrocarbons.
    """
    hc_mass = sum(
        x * GAS_COMPONENTS[k].molar_mass_kg_mol
        for k, x in comp.mole_fractions.items()
        if k in HYDROCARBONS
    )
    return comp.mole_fractions.get("CH4", 0.0) * M_CH4_KG_MOL / hc_mass


def ch4_hydrocarbon_mole_fraction(comp: GasComposition) -> float:
    """Return the CH4 share of hydrocarbon moles.

    Used to convert total-hydrocarbon volumes to CH4.

    Args:
        comp: Gas composition.

    Returns:
        x_CH4 divided by the sum of x_i over the hydrocarbons.
    """
    hc_moles = sum(x for k, x in comp.mole_fractions.items() if k in HYDROCARBONS)
    return comp.mole_fractions.get("CH4", 0.0) / hc_moles


def std_volume_to_ch4_kg(volume_sm3: float, comp: GasComposition) -> float:
    """Return the CH4 mass in a standard-condition gas volume.

    Args:
        volume_sm3: Gas volume in Sm3 (15 degC, 101325 Pa).
        comp: Gas composition.

    Returns:
        CH4 mass in kg, ``(P_STD*V/(R*T_STD)) * x_CH4 * M_CH4``.
    """
    moles = P_STD_PA * volume_sm3 / (R_J_MOL_K * T_STD_K)
    return moles * comp.mole_fractions.get("CH4", 0.0) * M_CH4_KG_MOL
