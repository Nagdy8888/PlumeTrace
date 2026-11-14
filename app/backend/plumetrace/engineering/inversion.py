"""Bayesian source inversion: which emission candidate leaks, at what rate, and how sure are we.

Hypotheses are the emission candidates plus "no source" (``NONE``). Every hypothesis gets a
posterior probability from a Gaussian likelihood of the window-mean sensor readings against the
Gaussian plume forward model, over a log-spaced rate grid. Weak or ambiguous evidence returns an
explicit ``inconclusive`` result, never a bare point estimate. Pure numpy, no I/O.
"""

import math
from typing import Final, Literal

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel

from plumetrace.engineering.averaging import CALM_WIND_M_S
from plumetrace.engineering.inversion_input import (
    DEFAULT_MODEL_REL_ERROR,
    DEFAULT_OBS_SIGMA_PPM,
    MAX_ABS_OBS_PPM,
    NO_SOURCE_ID,
    InversionInput,
)
from plumetrace.engineering.inversion_model import (
    RATE_GRID_KG_H,
    log_likelihood,
    unit_response_ppm,
)

__all__ = [
    "DEFAULT_MODEL_REL_ERROR",
    "DEFAULT_OBS_SIGMA_PPM",
    "MAX_ABS_OBS_PPM",
    "MIN_CONCLUSIVE_PROBABILITY",
    "MIN_SIGNAL_TO_NOISE",
    "MIN_USABLE_WINDOWS",
    "NO_SOURCE_ID",
    "NO_SOURCE_PRIOR",
    "CandidateScore",
    "InversionInput",
    "InversionResult",
    "Reason",
    "invert",
]

NO_SOURCE_PRIOR: Final = 0.5
MIN_CONCLUSIVE_PROBABILITY: Final = 0.6
MIN_SIGNAL_TO_NOISE: Final = 3.0
MIN_USABLE_WINDOWS: Final = 2

Reason = Literal["calm", "too_few_windows", "ambiguous", "weak_signal"]


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
    spread = None if inp.wind_dir_sd_deg is None else np.array(inp.wind_dir_sd_deg)[idx]
    response = unit_response_ppm(
        inp.candidates,
        inp.sensors,
        speed_m_s,
        from_deg,
        classes,
        inp.temp_k,
        inp.pressure_pa,
        inp.coeff,
        dir_sd_deg=spread,
    )
    ll = log_likelihood(
        obs[idx], response, RATE_GRID_KG_H / 3600.0, inp.obs_sigma_ppm, inp.model_rel_error
    )
    ids = [c.id for c in inp.candidates] + [NO_SOURCE_ID]
    return _summarise(ids, _posterior(ll), response, inp.obs_sigma_ppm, n_used)
