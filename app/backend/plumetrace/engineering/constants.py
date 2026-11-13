"""Physical constants and reference values used by the engineering core.

Every constant is defined here once, with its source. SI units; names carry the unit.
"""

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
