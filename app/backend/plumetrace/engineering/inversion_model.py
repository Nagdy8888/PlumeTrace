"""Numerics of the Bayesian source inversion: unit plume responses and the log-likelihood.

Pure numpy, no I/O. The public decision logic lives in ``inversion.py``.
"""

import math
from typing import Final

import numpy as np
import numpy.typing as npt

from plumetrace.engineering.dispersion import CoefficientSet
from plumetrace.engineering.geometry import Candidate, Sensor
from plumetrace.engineering.plume import concentration_ppm
from plumetrace.engineering.stability import StabilityClass

RATE_GRID_KG_H: Final = np.geomspace(0.1, 500.0, 80)


def unit_response_ppm(
    candidates: list[Candidate],
    sensors: list[Sensor],
    wind_speed_m_s: npt.NDArray[np.float64],
    wind_from_deg: npt.NDArray[np.float64],
    stability: list[StabilityClass],
    temp_k: float,
    pressure_pa: float,
    coeff: CoefficientSet,
) -> npt.NDArray[np.float64]:
    """Plume response of every sensor to 1 kg/s from every candidate in every window.

    Args:
        candidates: Possible emission points, ``C`` of them.
        sensors: Methane sensors, ``S`` of them.
        wind_speed_m_s: Wind speed per window in m/s, shape ``(W,)``, each above zero.
        wind_from_deg: Direction the wind blows from per window, shape ``(W,)``.
        stability: Pasquill class per window, length ``W``.
        temp_k: Air temperature in K.
        pressure_pa: Air pressure in Pa.
        coeff: Dispersion coefficient set.

    Returns:
        Concentration above background in ppm for a unit rate of 1 kg/s, shape ``(C, W, S)``.
    """
    receptors = np.array(
        [[s.position.x_m, s.position.y_m, s.position.z_m] for s in sensors], dtype=np.float64
    ).reshape(len(sensors), 3)
    out = np.zeros((len(candidates), len(wind_speed_m_s), len(sensors)))
    for c, candidate in enumerate(candidates):
        for w in range(len(wind_speed_m_s)):
            out[c, w] = concentration_ppm(
                1.0,
                float(wind_speed_m_s[w]),
                float(wind_from_deg[w]),
                candidate.position,
                receptors,
                stability[w],
                coeff,
                temp_k,
                pressure_pa,
            )
    return out


def log_likelihood(
    observed_ppm: npt.NDArray[np.float64],
    response: npt.NDArray[np.float64],
    rates_kg_s: npt.NDArray[np.float64],
    obs_sigma_ppm: float,
    model_rel_error: float,
) -> npt.NDArray[np.float64]:
    """Gaussian log-likelihood of the observations for every hypothesis and rate.

    For candidate ``c`` and rate ``q`` the prediction is ``response[c, w, s] * rates_kg_s[q]`` and
    the variance is ``obs_sigma_ppm**2 + (model_rel_error * prediction)**2``. NaN observations are
    skipped. The last row is the no-source hypothesis (prediction 0), identical for every rate.

    Args:
        observed_ppm: Observations above background, shape ``(W, S)``, NaN allowed.
        response: Unit responses in ppm per kg/s, shape ``(C, W, S)``.
        rates_kg_s: Rate grid in kg/s, shape ``(Q,)``.
        obs_sigma_ppm: Observation noise, one sigma, in ppm.
        model_rel_error: Relative one-sigma error of the plume model (fraction of the prediction).

    Returns:
        Log-likelihoods, shape ``(C + 1, Q)``.
    """
    valid = ~np.isnan(observed_ppm)
    y = np.where(valid, observed_ppm, 0.0)
    pred = response[:, None, :, :] * rates_kg_s[None, :, None, None]  # (C, Q, W, S)
    var = obs_sigma_ppm**2 + (model_rel_error * pred) ** 2
    terms = -0.5 * ((y - pred) ** 2 / var + np.log(2.0 * math.pi * var))
    ll = np.sum(np.where(valid, terms, 0.0), axis=(2, 3))
    var0 = obs_sigma_ppm**2
    none_terms = -0.5 * (y**2 / var0 + math.log(2.0 * math.pi * var0))
    ll_none = float(np.sum(np.where(valid, none_terms, 0.0)))
    return np.vstack([ll, np.full((1, len(rates_kg_s)), ll_none)])
