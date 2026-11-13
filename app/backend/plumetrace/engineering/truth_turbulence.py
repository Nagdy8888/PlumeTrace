"""Wind turbulence for the truth model: AR(1) meander of the direction and gusts of the speed.

Pure functions, no I/O; all randomness arrives as standard-normal draws made by the caller.
"""

import math

import numpy as np
import numpy.typing as npt

from plumetrace.engineering.truth_weather import InterpolatedWeather


def ar1_series(eps: npt.NDArray[np.float64], phi: float, sd: float) -> npt.NDArray[np.float64]:
    """AR(1) series with stationary standard deviation ``sd`` from standard-normal draws.

    ``x_0 = sd * eps_0`` and ``x_k = phi * x_{k-1} + sqrt(1 - phi^2) * sd * eps_k``. Used for the
    wind-direction meander and the gusty speed.

    Args:
        eps: Standard-normal draws, one per step.
        phi: Lag-one autocorrelation, 0 to 1.
        sd: Stationary standard deviation of the result.

    Returns:
        The series, same shape as ``eps``.
    """
    out = np.empty_like(eps)
    scale = math.sqrt(1.0 - phi * phi) * sd
    previous = 0.0
    for k in range(len(eps)):
        previous = sd * eps[k] if k == 0 else phi * previous + scale * eps[k]
        out[k] = previous
    return out


def turbulent_wind(
    base: InterpolatedWeather,
    eps: npt.NDArray[np.float64],
    dt_s: float,
    turbulence: tuple[float, float, float, float],
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Add wind meander to the direction and gusts to the speed.

    Both are AR(1) series with ``phi = exp(-dt_s / tau_s)``: the meander has a stationary
    standard deviation of ``meander_sd_deg``; the gusts multiply the speed by ``1 + r`` where
    ``r`` has a stationary standard deviation ``speed_cv``; the speed is then floored.

    Args:
        base: Interpolated hourly weather on the time axis.
        eps: Standard-normal draws, shape ``(T, 2)``: column 0 meander, column 1 gust.
        dt_s: Time step in seconds.
        turbulence: ``(tau_s, meander_sd_deg, speed_cv, min_speed_m_s)``.

    Returns:
        ``(from_deg, speed_m_s)``; direction in [0, 360).
    """
    tau_s, meander_sd_deg, speed_cv, min_speed_m_s = turbulence
    phi = math.exp(-dt_s / tau_s)
    from_deg = (base.from_deg + ar1_series(eps[:, 0], phi, meander_sd_deg)) % 360.0
    speed = np.maximum(min_speed_m_s, base.speed_m_s * (1.0 + ar1_series(eps[:, 1], phi, speed_cv)))
    return np.where(from_deg >= 360.0, 0.0, from_deg), speed
