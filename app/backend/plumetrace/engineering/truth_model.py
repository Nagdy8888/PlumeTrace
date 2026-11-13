"""Truth model: the deliberately different physics that generates sensor data.

The simulator and the benchmark use it so that the inversion never sees data made by its own
forward model. It differs on purpose: Pasquill-Gifford/Martin coefficients (the inversion uses
Briggs), wind meander, gusty speed, building-wake dilution, sensor noise and drift faults.
Random draws come only from the ``numpy.random.Generator`` passed in, so a seed fixes the output.
The module constants are Task 12 values (project choices, not published coefficients).
``WakeObstacle`` (``truth_wake``) and ``SensorFault`` (``truth_faults``) are re-exported here.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import numpy as np
import numpy.typing as npt

from plumetrace.engineering.constants import BACKGROUND_PPM
from plumetrace.engineering.dispersion import CoefficientSet
from plumetrace.engineering.geometry import Point3, Sensor
from plumetrace.engineering.plume import concentration_ppm
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.truth_faults import SensorFault, apply_faults
from plumetrace.engineering.truth_turbulence import turbulent_wind
from plumetrace.engineering.truth_wake import WakeObstacle, wake_mask
from plumetrace.engineering.truth_weather import (
    HourlyWeather,
    interpolate_weather,
    stability_series,
)
from plumetrace.engineering.units import kg_h_to_kg_s

__all__ = [
    "MIN_SPEED_M_S",
    "SensorFault",
    "TrueSource",
    "TruthConfig",
    "TruthSeries",
    "WakeObstacle",
    "simulate_sensors",
]

MIN_SPEED_M_S: Final = 0.3
# Guard against a time axis that would not fit in memory or finish in reasonable time.
_MAX_STEPS: Final = 200_000
# Keeps floor(0.3 / 0.1) at 3 despite floating-point rounding.
_TIME_TOLERANCE: Final = 1e-9


def _finite(*values: float) -> bool:
    """Whether every value is a finite number."""
    return all(math.isfinite(v) for v in values)


@dataclass(frozen=True)
class TruthConfig:
    """Parameters of the truth physics.

    Attributes:
        coeff: Dispersion coefficient set (the inversion uses Briggs rural).
        meander_sd_deg: Stationary standard deviation of the wind-direction meander, degrees.
        meander_tau_s: Correlation time of the meander and of the gusts, seconds (> 0).
        speed_cv: Stationary coefficient of variation of the gusty wind speed.
        wake_dilution: Factor applied once to the plume at a receptor in any building wake.
        noise_ppm: Standard deviation of the sensor noise, ppm.
        background_ppm: Methane background, ppm.
    """

    coeff: CoefficientSet = CoefficientSet.PG_MARTIN
    meander_sd_deg: float = 10.0
    meander_tau_s: float = 120.0
    speed_cv: float = 0.15
    wake_dilution: float = 0.6
    noise_ppm: float = 0.3
    background_ppm: float = BACKGROUND_PPM

    def __post_init__(self) -> None:
        """Reject values that are not finite or outside their physical range.

        Raises:
            ValueError: If a value is not finite, a spread, noise or background is negative,
                the correlation time is not above zero or the dilution is outside 0 to 1.
        """
        values = (self.meander_sd_deg, self.speed_cv, self.noise_ppm, self.background_ppm)
        if not _finite(*values, self.meander_tau_s, self.wake_dilution):
            raise ValueError("TruthConfig values must be finite")
        if min(values) < 0.0 or self.meander_tau_s <= 0.0 or not 0.0 <= self.wake_dilution <= 1.0:
            raise ValueError("TruthConfig: spreads and noise >= 0, tau > 0, dilution in 0 to 1")


@dataclass(frozen=True)
class TrueSource:
    """A real emission in the simulated world.

    Attributes:
        position: Emission point.
        rate_kg_h: Methane rate in kg/h (>= 0).
        start_s: Start time in seconds; the source is active from here.
        end_s: End time in seconds (exclusive; may be infinite), not before ``start_s``.
    """

    position: Point3
    rate_kg_h: float
    start_s: float
    end_s: float

    def __post_init__(self) -> None:
        """Reject a non-finite position, a negative rate or an inverted time window.

        Raises:
            ValueError: If the position, rate or start is not finite, the rate is negative, or
                ``end_s`` is NaN or before ``start_s``.
        """
        p = self.position
        if not _finite(p.x_m, p.y_m, p.z_m, self.rate_kg_h, self.start_s):
            raise ValueError("TrueSource position, rate_kg_h and start_s must be finite")
        if self.rate_kg_h < 0.0:
            raise ValueError("rate_kg_h must be >= 0")
        if not self.end_s >= self.start_s:
            raise ValueError("end_s must not be before start_s")


@dataclass(frozen=True)
class TruthSeries:
    """Simulated sensor readings and the weather that produced them.

    Attributes:
        times_s: Step times ``k * dt_s``, shape ``(T,)``.
        ppm: Absolute methane in ppm, shape ``(T, S)``, columns in sensor order.
        wind_speed_m_s: Gusty wind speed used at each step, shape ``(T,)``.
        wind_from_deg: Wind direction with meander in [0, 360), shape ``(T,)``.
        stability: Pasquill class at each step (from the speed without gusts), length ``T``.
        temp_k: Air temperature at each step, shape ``(T,)``.
    """

    times_s: npt.NDArray[np.float64]
    ppm: npt.NDArray[np.float64]
    wind_speed_m_s: npt.NDArray[np.float64]
    wind_from_deg: npt.NDArray[np.float64]
    stability: list[StabilityClass]
    temp_k: npt.NDArray[np.float64]


def _check_run(
    sensors: Sequence[Sensor],
    faults: Sequence[SensorFault],
    dt_s: float,
    duration_s: float,
    pressure_pa: float,
) -> int:
    """Validate the run set-up and return the number of time steps.

    Args:
        sensors: The sensors of the run.
        faults: The drift faults of the run.
        dt_s: Time step in seconds.
        duration_s: Run length in seconds.
        pressure_pa: Air pressure in Pa.

    Returns:
        ``floor(duration_s / dt_s)`` (with a tiny rounding tolerance).

    Raises:
        ValueError: If there are no sensors, ids repeat, a fault names an unknown sensor, the
            time axis or pressure is invalid, or the run would exceed the step cap.
    """
    ids = [s.id for s in sensors]
    if not ids:
        raise ValueError("sensors must not be empty")
    if len(set(ids)) != len(ids):
        raise ValueError("sensor ids must be unique")
    unknown = {f.sensor_id for f in faults} - set(ids)
    if unknown:
        raise ValueError(f"fault names unknown sensor {sorted(unknown)[0]}")
    if not (_finite(dt_s, duration_s, pressure_pa) and dt_s > 0.0 and pressure_pa > 0.0):
        raise ValueError("dt_s and pressure_pa must be > 0 and duration_s finite")
    if duration_s < dt_s:
        raise ValueError("duration_s must be at least dt_s")
    steps = duration_s / dt_s
    if not steps <= _MAX_STEPS:
        raise ValueError(f"duration_s / dt_s must not exceed {_MAX_STEPS} steps")
    return math.floor(steps + _TIME_TOLERANCE)


def _plume_step(
    sources: Sequence[TrueSource],
    receptors: npt.NDArray[np.float64],
    wind: tuple[float, float, StabilityClass, float],
    t_s: float,
    pressure_pa: float,
    wake: tuple[Sequence[WakeObstacle], TruthConfig],
) -> npt.NDArray[np.float64]:
    """Plume methane (ppm above background) at every receptor for one time step.

    Args:
        sources: All sources; only those active at ``t_s`` are summed.
        receptors: Receptor positions, shape ``(S, 3)``.
        wind: Speed (m/s), direction from (deg), stability class and temperature (K).
        t_s: Step time in seconds.
        pressure_pa: Air pressure in Pa.
        wake: Obstacles and the config (coefficient set and wake dilution).

    Returns:
        Excess concentration per receptor, shape ``(S,)``.
    """
    speed, from_deg, stability, temp_k = wind
    obstacles, config = wake
    plume = np.zeros(len(receptors), dtype=np.float64)
    for src in sources:
        if src.start_s <= t_s < src.end_s:
            plume += concentration_ppm(
                kg_h_to_kg_s(src.rate_kg_h),
                speed,
                from_deg,
                src.position,
                receptors,
                stability,
                config.coeff,
                temp_k,
                pressure_pa,
            )
    if obstacles:
        in_wake = wake_mask(obstacles, receptors[:, :2], from_deg)
        plume = np.where(in_wake, config.wake_dilution * plume, plume)
    return plume


def simulate_sensors(
    sources: list[TrueSource],
    sensors: list[Sensor],
    weather: list[HourlyWeather],
    dt_s: float,
    duration_s: float,
    rng: np.random.Generator,
    pressure_pa: float,
    obstacles: Sequence[WakeObstacle] = (),
    faults: Sequence[SensorFault] = (),
    config: TruthConfig = TruthConfig(),
) -> TruthSeries:
    """Simulate methane sensor readings with the truth physics.

    Args:
        sources: True emissions; each is active for ``start_s <= t < end_s``.
        sensors: Sensors; the column order of the result. Only their positions are used.
        weather: Hourly weather; hours past the list hold the last entry.
        dt_s: Time step in seconds (> 0).
        duration_s: Run length in seconds; ``floor(duration_s / dt_s)`` steps are made.
        rng: Seeded generator; per step it draws meander, gust, then one value per sensor.
        pressure_pa: Air pressure in Pa.
        obstacles: Building wakes.
        faults: Sensor drift faults.
        config: Truth physics parameters.

    Returns:
        The readings and the weather used.

    Raises:
        ValueError: If the inputs are invalid, or a reading is not finite (a rate too large).
    """
    steps = _check_run(sensors, faults, dt_s, duration_s, pressure_pa)
    times = np.arange(steps, dtype=np.float64) * dt_s
    base = interpolate_weather(weather, times)
    eps = rng.standard_normal((steps, 2 + len(sensors)))
    turbulence = (config.meander_tau_s, config.meander_sd_deg, config.speed_cv, MIN_SPEED_M_S)
    from_deg, speed = turbulent_wind(base, eps[:, :2], dt_s, turbulence)
    stability = stability_series(base)
    receptors = np.array([[s.position.x_m, s.position.y_m, s.position.z_m] for s in sensors])
    plume = np.zeros((steps, len(sensors)), dtype=np.float64)
    for k in range(steps):
        wind = (float(speed[k]), float(from_deg[k]), stability[k], float(base.temp_k[k]))
        plume[k] = _plume_step(sources, receptors, wind, times[k], pressure_pa, (obstacles, config))
    ppm = config.background_ppm + plume + config.noise_ppm * eps[:, 2:]
    apply_faults(ppm, times, sensors, faults)
    if not np.all(np.isfinite(ppm)):
        raise ValueError("a simulated reading is not finite (rate or drift too large)")
    return TruthSeries(times, ppm, speed, from_deg, stability, base.temp_k)
