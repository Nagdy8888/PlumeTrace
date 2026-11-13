"""Dispersion coefficient sets sigma_y and sigma_z for a Gaussian plume.

BRIGGS_RURAL: Briggs 1973, open country; Seinfeld & Pandis, Atmospheric Chemistry and Physics,
3rd ed., Table 18.3. x in m, sigma in m.
PG_MARTIN: Martin 1976 fit of the Pasquill-Gifford curves for x < 1 km; Cooper & Alley,
Air Pollution Control, Table 20-1.
Pure functions and constant tables, no I/O.
"""

from enum import StrEnum
from types import MappingProxyType
from typing import Final

import numpy as np
import numpy.typing as npt

from plumetrace.engineering.stability import StabilityClass


class CoefficientSet(StrEnum):
    """Which published sigma_y / sigma_z fit to evaluate."""

    BRIGGS_RURAL = "briggs_rural"
    PG_MARTIN = "pg_martin"


# Task 4 values: x is clipped to this range, and sigma is floored at SIGMA_MIN_M.
X_MIN_M: Final = 10.0
X_MAX_M: Final = 1000.0
SIGMA_MIN_M: Final = 0.5

_A, _B, _C, _D, _E, _F = (
    StabilityClass.A,
    StabilityClass.B,
    StabilityClass.C,
    StabilityClass.D,
    StabilityClass.E,
    StabilityClass.F,
)

# Briggs: sigma = k * x * (1 + b * x) ** p, one (k, b, p) triple per axis.
_BRIGGS_Y: Final = MappingProxyType(
    {
        _A: (0.22, 0.0001, -0.5),
        _B: (0.16, 0.0001, -0.5),
        _C: (0.11, 0.0001, -0.5),
        _D: (0.08, 0.0001, -0.5),
        _E: (0.06, 0.0001, -0.5),
        _F: (0.04, 0.0001, -0.5),
    }
)
_BRIGGS_Z: Final = MappingProxyType(
    {
        _A: (0.20, 0.0, 1.0),
        _B: (0.12, 0.0, 1.0),
        _C: (0.08, 0.0002, -0.5),
        _D: (0.06, 0.0015, -0.5),
        _E: (0.03, 0.0003, -1.0),
        _F: (0.016, 0.0003, -1.0),
    }
)
# Martin: sigma_y = a * x_km ** 0.894; sigma_z = c * x_km ** d + f; per class (a, c, d, f).
_MARTIN_EXPONENT_Y: Final = 0.894
_MARTIN: Final = MappingProxyType(
    {
        _A: (213.0, 440.8, 1.941, 9.27),
        _B: (156.0, 106.6, 1.149, 3.3),
        _C: (104.0, 61.0, 0.911, 0.0),
        _D: (68.0, 33.2, 0.725, -1.7),
        _E: (50.5, 22.8, 0.678, -1.3),
        _F: (34.0, 14.35, 0.740, -0.35),
    }
)


def _briggs(x_m: npt.NDArray[np.float64], k: float, b: float, p: float) -> npt.NDArray[np.float64]:
    """Evaluate ``k * x * (1 + b * x) ** p``."""
    return k * x_m * (1.0 + b * x_m) ** p


def sigmas_m(
    x_m: npt.NDArray[np.float64], stability: StabilityClass, coeff: CoefficientSet
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Horizontal and vertical plume spread at downwind distance ``x_m``.

    Args:
        x_m: Downwind distances in m. Clipped to [X_MIN_M, X_MAX_M] before evaluation.
        stability: Pasquill stability class.
        coeff: Coefficient set to evaluate.

    Returns:
        ``(sigma_y_m, sigma_z_m)``, both floored at SIGMA_MIN_M.
    """
    x = np.clip(x_m, X_MIN_M, X_MAX_M)
    if coeff is CoefficientSet.BRIGGS_RURAL:
        sy = _briggs(x, *_BRIGGS_Y[stability])
        sz = _briggs(x, *_BRIGGS_Z[stability])
    else:
        a, c, d, f = _MARTIN[stability]
        x_km = x / 1000.0
        sy = a * x_km**_MARTIN_EXPONENT_Y
        sz = c * x_km**d + f
    return np.maximum(sy, SIGMA_MIN_M), np.maximum(sz, SIGMA_MIN_M)
