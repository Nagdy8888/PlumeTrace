"""Atmospheric stability class by the Pasquill-Gifford-Turner scheme.

Source: Turner, D.B. (1994), Workbook of Atmospheric Dispersion Estimates, 2nd ed., Table 1-1.
Pure lookup tables, no I/O. Cells of the classic table that name two classes (for example A-B)
are resolved to the more stable letter: this is conservative, because a more stable class
predicts higher ground-level concentrations.
"""

from enum import StrEnum
from typing import Final


class StabilityClass(StrEnum):
    """Pasquill stability class, A (very unstable) to F (moderately stable)."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


# 600 and 300 W/m2 insolation bins and the 10 W/m2 day/night split: Phase 2 Task 3 thresholds
# (project choices, not Turner's own W/m2 values).
DAY_SHORTWAVE_W_M2: Final[float] = 10.0
STRONG_W_M2: Final[float] = 600.0
MODERATE_W_M2: Final[float] = 300.0
# Overcast is 7/8 cloud cover or more (Phase 2 Task 3 threshold); 0.5 is the night cloudy cut-off.
OVERCAST_FRACTION: Final[float] = 0.875
NIGHT_CLOUDY_FRACTION: Final[float] = 0.5

# Upper wind-speed edge (m/s) of each bin; the last bin is open ended.
_WIND_BIN_EDGES_M_S: Final[tuple[float, ...]] = (2.0, 3.0, 5.0, 6.0)

_A, _B, _C, _D, _E, _F = (
    StabilityClass.A,
    StabilityClass.B,
    StabilityClass.C,
    StabilityClass.D,
    StabilityClass.E,
    StabilityClass.F,
)

# Row per wind bin; key = insolation or night-sky condition.
_TABLE: Final[tuple[dict[str, StabilityClass], ...]] = (
    {"strong": _A, "moderate": _B, "slight": _B, "night_cloudy": _F, "night_clear": _F},
    {"strong": _B, "moderate": _B, "slight": _C, "night_cloudy": _E, "night_clear": _F},
    {"strong": _B, "moderate": _C, "slight": _C, "night_cloudy": _D, "night_clear": _E},
    {"strong": _C, "moderate": _D, "slight": _D, "night_cloudy": _D, "night_clear": _D},
    {"strong": _C, "moderate": _D, "slight": _D, "night_cloudy": _D, "night_clear": _D},
)


def _condition(shortwave_w_m2: float, cloud_fraction: float) -> str:
    """Name the table column: insolation by day, sky cover by night."""
    if shortwave_w_m2 > DAY_SHORTWAVE_W_M2:
        if shortwave_w_m2 > STRONG_W_M2:
            return "strong"
        return "moderate" if shortwave_w_m2 >= MODERATE_W_M2 else "slight"
    return "night_cloudy" if cloud_fraction >= NIGHT_CLOUDY_FRACTION else "night_clear"


def pasquill_class(
    wind_speed_m_s: float, shortwave_w_m2: float, cloud_fraction: float
) -> StabilityClass:
    """Classify atmospheric stability from wind, sunshine and cloud.

    Args:
        wind_speed_m_s: Wind speed at about 10 m height (m/s).
        shortwave_w_m2: Incoming shortwave radiation (W/m2); at or below 10 is night.
        cloud_fraction: Cloud cover as a fraction, 0 to 1.

    Returns:
        The stability class. Overcast (cloud fraction at least 0.875) is always D.
    """
    if cloud_fraction >= OVERCAST_FRACTION:
        return StabilityClass.D
    row = sum(wind_speed_m_s >= edge for edge in _WIND_BIN_EDGES_M_S)
    return _TABLE[row][_condition(shortwave_w_m2, cloud_fraction)]
