"""Gaussian plume forward model with total ground reflection.

Site coordinates are metres: x = east, y = north, z = up. Wind direction is the meteorological
"from" bearing in degrees clockwise from north.
"""

import math

import numpy as np
import numpy.typing as npt

from plumetrace.engineering.dispersion import X_MAX_M, X_MIN_M, CoefficientSet, sigmas_m
from plumetrace.engineering.geometry import Point3
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.units import kg_m3_to_ppm


def downwind_crosswind_m(
    source: Point3, receptors_xy: npt.NDArray[np.float64], wind_from_deg: float
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Rotate receptor positions into plume coordinates.

    The plume travels toward ``theta = radians(wind_from_deg + 180)``, clockwise from north.

    Args:
        source: Emission point.
        receptors_xy: Receptor positions, shape ``(N, 2)``, columns x and y in m.
        wind_from_deg: Direction the wind blows from, degrees clockwise from north.

    Returns:
        ``(along_m, cross_m)``: distance along the wind direction (positive downwind) and
        distance across it, each of shape ``(N,)``.
    """
    theta = math.radians(wind_from_deg + 180.0)
    dx = receptors_xy[:, 0] - source.x_m
    dy = receptors_xy[:, 1] - source.y_m
    along = dx * math.sin(theta) + dy * math.cos(theta)
    cross = dx * math.cos(theta) - dy * math.sin(theta)
    return along, cross


def _spreads(
    along: npt.NDArray[np.float64],
    stability: StabilityClass,
    coeff: CoefficientSet,
    dir_sd_deg: float,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Plume spreads from ``sigmas_m``, with ``sigma_y`` widened by the wind-direction spread.

    ``sigma_y,eff**2 = sigma_y**2 + (x_c * radians(dir_sd_deg))**2``, with ``x_c`` the along-wind
    distance clipped to ``[X_MIN_M, X_MAX_M]`` as ``sigmas_m`` clips it; ``sigma_z`` is unchanged.
    A spread of exactly 0.0 returns ``sigmas_m`` untouched.

    Raises:
        ValueError: If ``dir_sd_deg`` is negative or not finite.
    """
    if not (math.isfinite(dir_sd_deg) and dir_sd_deg >= 0.0):
        raise ValueError("dir_sd_deg must be >= 0 and finite")
    sy, sz = sigmas_m(along, stability, coeff)
    if dir_sd_deg == 0.0:
        return sy, sz
    x_c = np.clip(along, X_MIN_M, X_MAX_M)
    return np.sqrt(sy**2 + (x_c * math.radians(dir_sd_deg)) ** 2), sz


def _reflected_gaussian(
    rate_kg_s: float,
    wind_speed_m_s: float,
    along: npt.NDArray[np.float64],
    cross: npt.NDArray[np.float64],
    z_m: npt.NDArray[np.float64],
    h_m: float,
    sigmas: tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]],
) -> npt.NDArray[np.float64]:
    """Evaluate the reflected Gaussian formula and zero it where ``along <= 0``."""
    sy, sz = sigmas
    vertical = np.exp(-((z_m - h_m) ** 2) / (2.0 * sz**2))
    vertical = vertical + np.exp(-((z_m + h_m) ** 2) / (2.0 * sz**2))
    c = rate_kg_s / (2.0 * math.pi * wind_speed_m_s * sy * sz)
    c = c * np.exp(-(cross**2) / (2.0 * sy**2)) * vertical
    return np.where(along > 0.0, c, 0.0)


def concentration_kg_m3(
    rate_kg_s: float,
    wind_speed_m_s: float,
    wind_from_deg: float,
    source: Point3,
    receptors: npt.NDArray[np.float64],
    stability: StabilityClass,
    coeff: CoefficientSet,
    *,
    dir_sd_deg: float = 0.0,
) -> npt.NDArray[np.float64]:
    """Concentration above background (kg/m3) from a continuous point source.

    ``C = Q / (2 pi u sy sz) exp(-y^2 / 2 sy^2) [exp(-(z-H)^2 / 2 sz^2) + exp(-(z+H)^2 / 2 sz^2)]``,
    and ``C = 0`` where the receptor is not downwind. Symbols: ``Q`` rate_kg_s (kg/s); ``u``
    wind_speed_m_s (m/s); ``sy``, ``sz`` plume spreads from ``sigmas_m`` (m); ``y`` crosswind
    distance (m); ``z`` receptor height (m); ``H`` ``source.z_m`` (m); ``C`` result (kg/m3).
    Assumptions: steady state over the averaging period, flat terrain, no plume rise for vents,
    the 10 m wind used at all heights, total ground reflection. Reference: Turner, *Workbook of
    Atmospheric Dispersion Estimates*, 2nd ed., 1994. Optional ``dir_sd_deg`` widens ``sy`` for a
    wandering wind (project derivation, see ``_spreads``).

    Args:
        rate_kg_s: Emission rate in kg/s (>= 0).
        wind_speed_m_s: Wind speed in m/s (> 0).
        wind_from_deg: Direction the wind blows from, degrees clockwise from north.
        source: Emission point.
        receptors: Receptor positions, shape ``(N, 3)``, columns x, y, z in m.
        stability: Pasquill stability class.
        coeff: Dispersion coefficient set.
        dir_sd_deg: Within-window wind-direction standard deviation in degrees (>= 0). 0.0, the
            default, is the narrow plume of the formula above.

    Returns:
        Concentrations above background in kg/m3, shape ``(N,)``.

    Raises:
        ValueError: If ``wind_speed_m_s <= 0``, ``rate_kg_s < 0`` or ``dir_sd_deg`` is negative
            or not finite.
    """
    if wind_speed_m_s <= 0:
        raise ValueError("wind_speed_m_s must be > 0")
    if rate_kg_s < 0:
        raise ValueError("rate_kg_s must be >= 0")
    along, cross = downwind_crosswind_m(source, receptors[:, :2], wind_from_deg)
    sigmas = _spreads(along, stability, coeff, dir_sd_deg)
    return _reflected_gaussian(
        rate_kg_s, wind_speed_m_s, along, cross, receptors[:, 2], source.z_m, sigmas
    )


def concentration_ppm(
    rate_kg_s: float,
    wind_speed_m_s: float,
    wind_from_deg: float,
    source: Point3,
    receptors: npt.NDArray[np.float64],
    stability: StabilityClass,
    coeff: CoefficientSet,
    temp_k: float,
    pressure_pa: float,
    *,
    dir_sd_deg: float = 0.0,
) -> npt.NDArray[np.float64]:
    """Concentration above background as a methane mole fraction in ppm.

    Args:
        rate_kg_s: Emission rate in kg/s (>= 0).
        wind_speed_m_s: Wind speed in m/s (> 0).
        wind_from_deg: Direction the wind blows from, degrees clockwise from north.
        source: Emission point.
        receptors: Receptor positions, shape ``(N, 3)``, columns x, y, z in m.
        stability: Pasquill stability class.
        coeff: Dispersion coefficient set.
        temp_k: Air temperature in K.
        pressure_pa: Air pressure in Pa.
        dir_sd_deg: Within-window wind-direction standard deviation in degrees (>= 0); see
            ``concentration_kg_m3``.

    Returns:
        Concentrations above background in ppm, shape ``(N,)``.

    Raises:
        ValueError: As ``concentration_kg_m3``.
    """
    conc = concentration_kg_m3(
        rate_kg_s,
        wind_speed_m_s,
        wind_from_deg,
        source,
        receptors,
        stability,
        coeff,
        dir_sd_deg=dir_sd_deg,
    )
    return np.asarray(kg_m3_to_ppm(conc, temp_k, pressure_pa), dtype=np.float64)
