"""Physical constants and reference values used by the engineering core.

Every constant is defined here once, with its source. SI units; names carry the unit.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

# source: CODATA 2018 molar gas constant
R_J_MOL_K: Final[float] = 8.314462618
# source: NIST Chemistry WebBook, methane
M_CH4_KG_MOL: Final[float] = 0.016043
# source: ISO 13443 standard reference conditions (15 °C)
T_STD_K: Final[float] = 288.15
# source: ISO 13443 standard reference conditions
P_STD_PA: Final[float] = 101325.0
# source: exact (1 ft = 0.3048 m)
FT3_TO_M3: Final[float] = 0.028316846592
# source: IPCC AR6 WG1 Ch. 7, Table 7.15 (fossil CH4)
GWP100_CH4_FOSSIL: Final[float] = 29.8
# source: IPCC AR6 WG1 Ch. 7, Table 7.15 (fossil CH4)
GWP20_CH4_FOSSIL: Final[float] = 82.5
# source: approximate global mean surface CH4 (design §5)
BACKGROUND_PPM: Final[float] = 1.95
# source: non-leap year
HOURS_PER_YEAR: Final[float] = 8760.0


@dataclass(frozen=True)
class ComponentProperties:
    """Molar mass and critical constants of one gas component (SI units)."""

    molar_mass_kg_mol: float
    critical_temp_k: float
    critical_pressure_pa: float


# source: NIST Chemistry WebBook (molar masses, critical constants), retrieved 2026-11.
GAS_COMPONENTS: Final[Mapping[str, ComponentProperties]] = MappingProxyType(
    {
        "CH4": ComponentProperties(0.016043, 190.56, 4.599e6),
        "C2H6": ComponentProperties(0.03007, 305.32, 4.872e6),
        "C3H8": ComponentProperties(0.044097, 369.83, 4.248e6),
        "nC4H10": ComponentProperties(0.05812, 425.12, 3.796e6),
        "CO2": ComponentProperties(0.04401, 304.13, 7.377e6),
        "N2": ComponentProperties(0.028013, 126.2, 3.396e6),
    }
)
HYDROCARBONS: Final[frozenset[str]] = frozenset({"CH4", "C2H6", "C3H8", "nC4H10"})
