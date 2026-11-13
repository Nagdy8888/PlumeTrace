"""Bayesian source inversion: which emission candidate leaks, at what rate, and how sure are we.

Hypotheses are the emission candidates plus "no source" (``NONE``). Every hypothesis gets a
posterior probability from a Gaussian likelihood of the window-mean sensor readings against the
Gaussian plume forward model, over a log-spaced rate grid. Weak or ambiguous evidence returns an
explicit ``inconclusive`` result, never a bare point estimate. Pure numpy, no I/O.
"""

import math
from typing import Final, Literal, Self

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, model_validator

from plumetrace.engineering.averaging import CALM_WIND_M_S
from plumetrace.engineering.dispersion import CoefficientSet
from plumetrace.engineering.geometry import Candidate, Sensor
from plumetrace.engineering.inversion_model import (
    RATE_GRID_KG_H,
    log_likelihood,
    unit_response_ppm,
)
from plumetrace.engineering.stability import StabilityClass

NO_SOURCE_ID: Final = "NONE"
NO_SOURCE_PRIOR: Final = 0.5
MIN_CONCLUSIVE_PROBABILITY: Final = 0.6
MIN_SIGNAL_TO_NOISE: Final = 3.0
MIN_USABLE_WINDOWS: Final = 2
DEFAULT_OBS_SIGMA_PPM: Final = 0.1
DEFAULT_MODEL_REL_ERROR: Final = 0.6
MAX_ABS_OBS_PPM: Final = 1.0e6  # pure methane; a mole-fraction difference cannot exceed it

Reason = Literal["calm", "too_few_windows", "ambiguous", "weak_signal"]


class InversionInput(BaseModel):
    """Everything the inversion needs for one event.

    Attributes:
        candidates: Possible emission points (``C``), ids unique and never ``NONE``.
        sensors: Methane sensors (``S``).
        observed_ppm_above_bg: Window means above background, ``W`` rows of ``S`` values; NaN or
            infinite values are treated as missing. Every finite value must satisfy
            ``abs(value) <= MAX_ABS_OBS_PPM``, otherwise the input is rejected.
        wind_speed_m_s: Mean wind speed per window in m/s; NaN means unknown. A finite value must
            be >= 0, otherwise the input is rejected.
        wind_from_deg: Mean wind "from" bearing per window, degrees clockwise from north.
        stability: Pasquill class per window.
        temp_k: Air temperature in K.
        pressure_pa: Air pressure in Pa.
        obs_sigma_ppm: Observation noise, one sigma, in ppm (> 0).
        model_rel_error: Relative one-sigma error of the plume model (>= 0).
        coeff: Dispersion coefficient set.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    candidates: list[Candidate]
    sensors: list[Sensor]
    observed_ppm_above_bg: list[list[float]]
    wind_speed_m_s: list[float]
    wind_from_deg: list[float]
    stability: list[StabilityClass]
    temp_k: float
    pressure_pa: float
    obs_sigma_ppm: float = DEFAULT_OBS_SIGMA_PPM
    model_rel_error: float = DEFAULT_MODEL_REL_ERROR
    coeff: CoefficientSet = CoefficientSet.BRIGGS_RURAL

    @model_validator(mode="after")
    def _check(self) -> Self:
        """Reject empty or inconsistent input instead of returning a meaningless posterior."""
        ids = [c.id for c in self.candidates]
        if not ids or not self.sensors:
            raise ValueError("candidates and sensors must not be empty")
        if NO_SOURCE_ID in ids or len(set(ids)) != len(ids):
            raise ValueError(f"candidate ids must be unique and not {NO_SOURCE_ID!r}")
        n = len(self.observed_ppm_above_bg)
        if not (len(self.wind_speed_m_s) == len(self.wind_from_deg) == len(self.stability) == n):
            raise ValueError(
                "wind, stability and observation arrays must have one entry per window"
            )
        if any(len(row) != len(self.sensors) for row in self.observed_ppm_above_bg):
            raise ValueError("every observation row must have one value per sensor")
        obs = np.array(self.observed_ppm_above_bg, dtype=np.float64)
        if np.any(np.abs(obs[np.isfinite(obs)]) > MAX_ABS_OBS_PPM):
            raise ValueError(
                "finite observed_ppm_above_bg values must be within -1e6 and 1e6 ppm "
                "(1e6 ppm is pure methane)"
            )
        speed = np.array(self.wind_speed_m_s, dtype=np.float64)
        if np.any(speed[np.isfinite(speed)] < 0.0):
            raise ValueError("wind_speed_m_s values must be >= 0 or NaN (unknown)")
        positive = (self.obs_sigma_ppm, self.temp_k, self.pressure_pa)
        if not all(v > 0.0 and math.isfinite(v) for v in positive):
            raise ValueError("obs_sigma_ppm, temp_k and pressure_pa must be positive and finite")
        if not (self.model_rel_error >= 0.0 and math.isfinite(self.model_rel_error)):
            raise ValueError("model_rel_error must be >= 0 and finite")
        return self


class CandidateScore(BaseModel):
    """Posterior probability of one hypothesis.

    Attributes:
        id: Candidate id, or ``NONE`` for the no-source hypothesis.
        probability: Posterior probability, 0 to 1.
    """

    id: str
    probability: float


class InversionResult(BaseModel):
    """Outcome of the inversion for one event.

    Attributes:
        ranked: All hypotheses, highest probability first (ties by id); empty when no usable data.
        top_id: Most probable hypothesis id (``NONE`` when no source or no usable data).
        top_probability: Its posterior probability (0.0 when no usable data).
        rate_kg_h: Median rate of the top candidate in kg/h; None when the top is ``NONE``.
        rate_p05_kg_h: 5th percentile of the rate in kg/h.
        rate_p95_kg_h: 95th percentile of the rate in kg/h.
        rate_at_grid_edge: True when the median sits at either end of the rate grid.
        inconclusive: True when the evidence does not support a conclusion.
        reason: Why it is inconclusive; None when conclusive.
        windows_used: Windows that entered the likelihood.
    """

    ranked: list[CandidateScore]
    top_id: str
    top_probability: float
    rate_kg_h: float | None
    rate_p05_kg_h: float | None
    rate_p95_kg_h: float | None
    rate_at_grid_edge: bool
    inconclusive: bool
    reason: Reason | None
    windows_used: int


def _none_result(
    ranked: list[CandidateScore], top_p: float, reason: Reason | None, windows_used: int
) -> InversionResult:
    """Result whose top hypothesis is no source: no rate; inconclusive exactly when ``reason``."""
    return InversionResult(
        ranked=ranked,
        top_id=NO_SOURCE_ID,
        top_probability=top_p,
        rate_kg_h=None,
        rate_p05_kg_h=None,
        rate_p95_kg_h=None,
        rate_at_grid_edge=False,
        inconclusive=reason is not None,
        reason=reason,
        windows_used=windows_used,
    )


def _observations(inp: InversionInput) -> npt.NDArray[np.float64]:
    """Observation matrix ``(W, S)`` with every non-finite value turned into NaN."""
    obs = np.array(inp.observed_ppm_above_bg, dtype=np.float64)
    obs = obs.reshape(len(inp.observed_ppm_above_bg), len(inp.sensors))
    return np.where(np.isfinite(obs), obs, np.nan)


def _usable_windows(inp: InversionInput, obs: npt.NDArray[np.float64]) -> npt.NDArray[np.bool_]:
    """Windows with a known, non-calm wind and at least one valid observation."""
    speed = np.array(inp.wind_speed_m_s, dtype=np.float64)
    wind_ok = np.isfinite(speed) & np.isfinite(np.array(inp.wind_from_deg, dtype=np.float64))
    return wind_ok & (speed >= CALM_WIND_M_S) & np.any(~np.isnan(obs), axis=1)


def _all_calm(inp: InversionInput) -> bool:
    """True when there are windows and every one has a known wind speed below the calm limit."""
    speed = np.array(inp.wind_speed_m_s, dtype=np.float64)
    return speed.size > 0 and bool(np.all(np.isfinite(speed) & (speed < CALM_WIND_M_S)))


def _posterior(ll: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Posterior over ``(C + 1, Q)`` by log-sum-exp normalisation of likelihood plus log prior."""
    n_cand, n_rates = ll.shape[0] - 1, ll.shape[1]
    prior = np.full(n_cand + 1, math.log((1.0 - NO_SOURCE_PRIOR) / n_cand))
    prior[-1] = math.log(NO_SOURCE_PRIOR)
    log_post = ll + prior[:, None] - math.log(n_rates)
    peak = np.max(log_post)
    if not math.isfinite(peak):
        raise ValueError(
            "inversion posterior is not finite; check obs_sigma_ppm and the observations"
        )
    log_norm = peak + math.log(float(np.sum(np.exp(log_post - peak))))
    return np.exp(log_post - log_norm)


def _rate_percentiles_kg_h(rate_posterior: npt.NDArray[np.float64]) -> tuple[float, float, float]:
    """Median, 5th and 95th percentile in kg/h from a posterior over ``RATE_GRID_KG_H``."""
    cdf = np.cumsum(rate_posterior / np.sum(rate_posterior))
    log_grid = np.log(RATE_GRID_KG_H)
    median, p05, p95 = (float(np.exp(np.interp(q, cdf, log_grid))) for q in (0.5, 0.05, 0.95))
    return median, p05, p95


def _decision(top_p: float, peak_ppm: float | None, obs_sigma_ppm: float) -> Reason | None:
    """Reason the result is inconclusive, or None; ``peak_ppm`` is None for a ``NONE`` top."""
    if top_p < MIN_CONCLUSIVE_PROBABILITY:
        return "ambiguous"
    if peak_ppm is not None and peak_ppm < MIN_SIGNAL_TO_NOISE * obs_sigma_ppm:
        return "weak_signal"
    return None


def _summarise(
    ids: list[str],
    joint: npt.NDArray[np.float64],
    response: npt.NDArray[np.float64],
    obs_sigma_ppm: float,
    n_used: int,
) -> InversionResult:
    """Rank the hypotheses, estimate the top candidate's rate and apply the decision rules.

    Args:
        ids: Candidate ids followed by ``NONE``, matching the rows of ``joint``.
        joint: Posterior over ``(C + 1, Q)``.
        response: Unit responses of the used windows, shape ``(C, W, S)``.
        obs_sigma_ppm: Observation noise in ppm.
        n_used: Number of windows used.

    Returns:
        The inversion result.
    """
    probs = joint.sum(axis=1)
    order = sorted(range(len(ids)), key=lambda i: (-probs[i], ids[i]))
    ranked = [CandidateScore(id=ids[i], probability=float(probs[i])) for i in order]
    top = order[0]
    top_p = float(probs[top])
    if ids[top] == NO_SOURCE_ID:
        return _none_result(ranked, top_p, _decision(top_p, None, obs_sigma_ppm), n_used)
    median, p05, p95 = _rate_percentiles_kg_h(joint[top])
    reason = _decision(top_p, float(np.max(response[top])) * median / 3600.0, obs_sigma_ppm)
    edge = median <= RATE_GRID_KG_H[1] or median >= RATE_GRID_KG_H[-2]
    return InversionResult(
        ranked=ranked,
        top_id=ids[top],
        top_probability=top_p,
        rate_kg_h=median,
        rate_p05_kg_h=p05,
        rate_p95_kg_h=p95,
        rate_at_grid_edge=bool(edge),
        inconclusive=reason is not None,
        reason=reason,
        windows_used=n_used,
    )


def invert(inp: InversionInput) -> InversionResult:
    """Rank the emission candidates and estimate the leak rate of the most probable one.

    Windows are used only when wind speed and direction are known, the wind is at least
    ``CALM_WIND_M_S`` and at least one sensor has a valid reading. Fewer than
    ``MIN_USABLE_WINDOWS`` gives an inconclusive result (``calm`` when every window is calm,
    otherwise ``too_few_windows``). The no-source hypothesis has prior ``NO_SOURCE_PRIOR``; the
    remaining prior is shared equally by the candidates. The rate is a median with a 90 % interval
    from the posterior over ``RATE_GRID_KG_H``.

    Args:
        inp: Candidates, sensors, window means, wind, stability and error model.

    Returns:
        The ranked hypotheses, the rate of the top candidate (None if the top is no source),
        and the inconclusive flag with its reason.
    """
    obs = _observations(inp)
    usable = _usable_windows(inp, obs)
    n_used = int(np.sum(usable))
    if n_used < MIN_USABLE_WINDOWS:
        return _none_result([], 0.0, "calm" if _all_calm(inp) else "too_few_windows", n_used)
    idx = np.flatnonzero(usable)
    speed_m_s = np.array(inp.wind_speed_m_s, dtype=np.float64)[idx]
    from_deg = np.array(inp.wind_from_deg, dtype=np.float64)[idx]
    classes = [inp.stability[i] for i in idx]
    response = unit_response_ppm(
        inp.candidates,
        inp.sensors,
        speed_m_s,
        from_deg,
        classes,
        inp.temp_k,
        inp.pressure_pa,
        inp.coeff,
    )
    ll = log_likelihood(
        obs[idx], response, RATE_GRID_KG_H / 3600.0, inp.obs_sigma_ppm, inp.model_rel_error
    )
    ids = [c.id for c in inp.candidates] + [NO_SOURCE_ID]
    return _summarise(ids, _posterior(ll), response, inp.obs_sigma_ppm, n_used)
