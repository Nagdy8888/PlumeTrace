"""Hourly weather for the truth model: a synthetic generator and a time interpolator.

The simulator (Phase 3) fills ``HourlyWeather`` from Open-Meteo; ``synthetic_hourly_weather``
gives deterministic stand-in weather for tests and the benchmark. All constants below are
Phase 2 Task 12 values (project choices, not published coefficients). Directions are
meteorological "from" bearings in degrees clockwise from north.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field

from plumetrace.engineering.stability import StabilityClass, pasquill_class

_SPEED_MEDIAN_M_S: Final = 4.0
_SPEED_LOG_SD: Final = 0.5
_SPEED_MIN_M_S: Final = 0.3
_SPEED_MAX_M_S: Final = 15.0
_DIRECTION_STEP_SD_DEG: Final = 20.0
_DIRECTION_RESTORING: Final = 0.2
_CLOUD_BETA_A: Final = 2.0
_CLOUD_BETA_B: Final = 5.0
_SUNRISE_H: Final = 6
_SUNSET_H: Final = 18
_PEAK_SHORTWAVE_W_M2: Final = 800.0
_CLOUD_SHORTWAVE_LOSS: Final = 0.75
_WARM_SHORTWAVE_W_M2: Final = 10.0
_DAY_TEMP_K: Final = 300.0
_NIGHT_TEMP_K: Final = 285.0


class HourlyWeather(BaseModel):
    """One hour of weather. Non-finite or unphysical values are rejected at construction.

    Attributes:
        hour_index: Hours since the start of the series (>= 0).
        wind_speed_m_s: Wind speed in m/s (>= 0; a calm hour is allowed).
        wind_from_deg: Direction the wind blows from, degrees clockwise from north.
        shortwave_w_m2: Incoming shortwave radiation in W/m2 (>= 0).
        cloud_fraction: Cloud cover as a fraction, 0 to 1.
        temp_k: Air temperature in K (> 0).
    """

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    hour_index: int = Field(ge=0)
    wind_speed_m_s: float = Field(ge=0.0)
    wind_from_deg: float
    shortwave_w_m2: float = Field(ge=0.0)
    cloud_fraction: float = Field(ge=0.0, le=1.0)
    temp_k: float = Field(gt=0.0)


@dataclass(frozen=True)
class InterpolatedWeather:
    """Hourly weather evaluated on a time axis; every array has the shape of the times.

    Attributes:
        speed_m_s: Wind speed, linear between hours.
        from_deg: Wind direction in [0, 360), linear along the shortest arc between hours.
        temp_k: Air temperature of the hour containing each time.
        shortwave_w_m2: Shortwave radiation of the hour containing each time.
        cloud_fraction: Cloud fraction of the hour containing each time.
    """

    speed_m_s: npt.NDArray[np.float64]
    from_deg: npt.NDArray[np.float64]
    temp_k: npt.NDArray[np.float64]
    shortwave_w_m2: npt.NDArray[np.float64]
    cloud_fraction: npt.NDArray[np.float64]


def _arc_diff(
    a_deg: npt.NDArray[np.float64], b_deg: npt.NDArray[np.float64]
) -> npt.NDArray[np.float64]:
    """Signed smallest angle ``a - b`` in (-180, 180], elementwise.

    Args:
        a_deg: First bearings in degrees.
        b_deg: Second bearings in degrees.

    Returns:
        The differences in degrees.
    """
    diff = np.asarray((a_deg - b_deg) % 360.0, dtype=np.float64)
    return np.asarray(np.where(diff > 180.0, diff - 360.0, diff), dtype=np.float64)


def angular_diff_deg(a_deg: float, b_deg: float) -> float:
    """Signed smallest difference ``a - b`` between two bearings.

    Args:
        a_deg: First bearing in degrees.
        b_deg: Second bearing in degrees.

    Returns:
        The difference in degrees, in (-180, 180].
    """
    return float(
        _arc_diff(np.asarray(a_deg, dtype=np.float64), np.asarray(b_deg, dtype=np.float64))
    )


def _sunshine_w_m2(hour_of_day: int, cloud_fraction: float) -> float:
    """Clear-sky shortwave of the hour, reduced by cloud; zero outside 06 to 18 h.

    Args:
        hour_of_day: Local clock hour, 0 to 23.
        cloud_fraction: Cloud cover as a fraction, 0 to 1.

    Returns:
        Shortwave radiation in W/m2.
    """
    if not _SUNRISE_H <= hour_of_day <= _SUNSET_H:
        return 0.0
    clear = max(0.0, _PEAK_SHORTWAVE_W_M2 * math.sin(math.pi * (hour_of_day - _SUNRISE_H) / 12.0))
    return clear * (1.0 - _CLOUD_SHORTWAVE_LOSS * cloud_fraction)


def _check_generator_input(hours: int, start_hour_of_day: int, prevailing_from_deg: float) -> None:
    """Reject a negative count, a start hour outside 0 to 23 or a non-finite direction.

    Args:
        hours: Number of hours requested.
        start_hour_of_day: Local clock hour of hour 0.
        prevailing_from_deg: Prevailing wind-from direction in degrees.

    Raises:
        ValueError: If an argument is outside its range.
    """
    if hours < 0:
        raise ValueError("hours must be >= 0")
    if not 0 <= start_hour_of_day <= 23:
        raise ValueError("start_hour_of_day must be 0 to 23")
    if not math.isfinite(prevailing_from_deg):
        raise ValueError("prevailing_from_deg must be finite")


def synthetic_hourly_weather(
    hours: int,
    start_hour_of_day: int,
    rng: np.random.Generator,
    prevailing_from_deg: float = 250.0,
) -> list[HourlyWeather]:
    """Generate deterministic hourly weather for tests and the benchmark.

    Per hour, in this draw order: speed normal, direction normal, cloud beta. Speed is
    log-normal (median 4 m/s) clipped to 0.3 to 15 m/s; direction is a mean-reverting random
    walk around the prevailing direction; shortwave follows a half sine from 06 to 18 h local
    time, reduced by cloud; temperature is 300 K by day and 285 K by night.

    Args:
        hours: Number of hours to generate (>= 0).
        start_hour_of_day: Local clock hour of hour 0, 0 to 23.
        rng: Seeded random generator; the only source of randomness.
        prevailing_from_deg: Prevailing wind-from direction in degrees.

    Returns:
        ``hours`` entries with ``hour_index`` 0, 1, 2, and so on.

    Raises:
        ValueError: If ``hours`` is negative, ``start_hour_of_day`` is outside 0 to 23 or
            ``prevailing_from_deg`` is not finite.
    """
    _check_generator_input(hours, start_hour_of_day, prevailing_from_deg)
    direction = prevailing_from_deg
    series: list[HourlyWeather] = []
    for i in range(hours):
        speed = math.exp(math.log(_SPEED_MEDIAN_M_S) + _SPEED_LOG_SD * rng.normal(0.0, 1.0))
        pull = _DIRECTION_RESTORING * angular_diff_deg(direction, prevailing_from_deg)
        direction = (direction + rng.normal(0.0, _DIRECTION_STEP_SD_DEG) - pull) % 360.0
        direction = 0.0 if direction >= 360.0 else direction
        cloud = float(rng.beta(_CLOUD_BETA_A, _CLOUD_BETA_B))
        shortwave = _sunshine_w_m2((start_hour_of_day + i) % 24, cloud)
        series.append(
            HourlyWeather(
                hour_index=i,
                wind_speed_m_s=min(max(speed, _SPEED_MIN_M_S), _SPEED_MAX_M_S),
                wind_from_deg=direction,
                shortwave_w_m2=shortwave,
                cloud_fraction=cloud,
                temp_k=_DAY_TEMP_K if shortwave > _WARM_SHORTWAVE_W_M2 else _NIGHT_TEMP_K,
            )
        )
    return series


def interpolate_weather(
    weather: Sequence[HourlyWeather], times_s: npt.NDArray[np.float64]
) -> InterpolatedWeather:
    """Evaluate hourly weather at the given times.

    With ``h = t / 3600``, ``i = floor(h)`` and ``f = h - i``: speed is linear between hour
    ``i`` and ``i + 1``, direction is linear along the shortest arc, temperature, shortwave and
    cloud come from hour ``i``. Hours beyond the list hold the last entry.

    Args:
        weather: Hourly weather, entry ``i`` valid from ``3600 * i`` s (list position).
        times_s: Times in seconds since the start, finite and >= 0.

    Returns:
        The interpolated weather, arrays of the same length as ``times_s``.

    Raises:
        ValueError: If ``weather`` is empty or a time is negative or not finite.
    """
    if len(weather) == 0:
        raise ValueError("weather must not be empty")
    if not np.all(np.isfinite(times_s)) or np.any(times_s < 0.0):
        raise ValueError("times_s must be finite and >= 0")
    last = len(weather) - 1
    hours = times_s / 3600.0
    floor_h = np.floor(hours)
    lo = np.minimum(floor_h, last).astype(np.intp)
    hi = np.minimum(floor_h + 1.0, last).astype(np.intp)
    frac = hours - floor_h

    def column(name: str) -> npt.NDArray[np.float64]:
        """Collect one ``HourlyWeather`` field over all hours as an array."""
        return np.array([getattr(w, name) for w in weather], dtype=np.float64)

    speed, bearing = column("wind_speed_m_s"), column("wind_from_deg")
    from_deg = bearing[lo] + frac * _arc_diff(bearing[hi], bearing[lo])
    from_deg = np.asarray(from_deg % 360.0, dtype=np.float64)
    return InterpolatedWeather(
        speed_m_s=speed[lo] + frac * (speed[hi] - speed[lo]),
        from_deg=np.where(from_deg >= 360.0, 0.0, from_deg),
        temp_k=column("temp_k")[lo],
        shortwave_w_m2=column("shortwave_w_m2")[lo],
        cloud_fraction=column("cloud_fraction")[lo],
    )


def stability_series(base: InterpolatedWeather) -> list[StabilityClass]:
    """Pasquill class at each time from the interpolated speed (no gusts), sun and cloud.

    Args:
        base: Interpolated hourly weather.

    Returns:
        One class per time step.
    """
    return [
        pasquill_class(float(u), float(sw), float(c))
        for u, sw, c in zip(base.speed_m_s, base.shortwave_w_m2, base.cloud_fraction, strict=True)
    ]
