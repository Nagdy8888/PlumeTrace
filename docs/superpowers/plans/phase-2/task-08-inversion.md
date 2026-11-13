# Phase 2 · Task 8 — Bayesian source inversion

**Skills:** `plan-execution`, `engineering-core`, `project-documentation`.

The method and decision rules below were validated by the planner with a prototype on the KS-07
layout (source recovered at p = 1.0; pure noise → `NONE` with p ≈ 0.82 over 5 seeds; mirror-symmetric
pair → p = 0.5 → inconclusive; 36 windows run in ≈ 0.04 s).

## Files
Create `app/backend/plumetrace/engineering/inversion_model.py`, `app/backend/plumetrace/engineering/inversion.py`, `app/backend/tests/engineering/test_inversion.py`.

## Interface

`inversion_model.py` (numerics only):
- `RATE_GRID_KG_H: Final = np.geomspace(0.1, 500.0, 80)`
- `def unit_response_ppm(candidates: list[Candidate], sensors: list[Sensor], wind_speed_m_s: npt.NDArray[np.float64], wind_from_deg: npt.NDArray[np.float64], stability: list[StabilityClass], temp_k: float, pressure_pa: float, coeff: CoefficientSet) -> npt.NDArray[np.float64]` → shape `(C, W, S)`: ppm at each sensor for **1 kg/s** from each candidate in each window (`concentration_ppm` with `rate_kg_s=1.0`).
- `def log_likelihood(observed_ppm: npt.NDArray[np.float64], response: npt.NDArray[np.float64], rates_kg_s: npt.NDArray[np.float64], obs_sigma_ppm: float, model_rel_error: float) -> npt.NDArray[np.float64]` → shape `(C + 1, Q)`:
  - `pred[c, q, w, s] = response[c, w, s] · rates_kg_s[q]`; `var = obs_sigma_ppm² + (model_rel_error · pred)²`;
  - `ll[c, q] = Σ_{w,s non-NaN} −½·((y − pred)²/var + ln(2π·var))`;
  - row `C` is the no-source hypothesis: `pred = 0`, `var = obs_sigma_ppm²`, same value for every q.

`inversion.py` (public API and decisions):
- Constants: `NO_SOURCE_ID = "NONE"`; `NO_SOURCE_PRIOR = 0.5`; `MIN_CONCLUSIVE_PROBABILITY = 0.6`; `MIN_SIGNAL_TO_NOISE = 3.0`; `MIN_USABLE_WINDOWS = 2`; `DEFAULT_OBS_SIGMA_PPM = 0.1`; `DEFAULT_MODEL_REL_ERROR = 0.6`.
- `class InversionInput(BaseModel)` (`arbitrary_types_allowed=True`): `candidates: list[Candidate]`, `sensors: list[Sensor]`, `observed_ppm_above_bg: list[list[float]]` (W × S, NaN allowed), `wind_speed_m_s: list[float]`, `wind_from_deg: list[float]`, `stability: list[StabilityClass]`, `temp_k: float`, `pressure_pa: float`, `obs_sigma_ppm: float = DEFAULT_OBS_SIGMA_PPM`, `model_rel_error: float = DEFAULT_MODEL_REL_ERROR`, `coeff: CoefficientSet = CoefficientSet.BRIGGS_RURAL`.
- `class CandidateScore(BaseModel)`: `id: str`, `probability: float`.
- `class InversionResult(BaseModel)`: `ranked: list[CandidateScore]` (descending probability, includes `NONE`), `top_id: str`, `top_probability: float`, `rate_kg_h: float | None`, `rate_p05_kg_h: float | None`, `rate_p95_kg_h: float | None`, `rate_at_grid_edge: bool`, `inconclusive: bool`, `reason: Literal["calm", "too_few_windows", "ambiguous", "weak_signal"] | None`, `windows_used: int`.
- `def invert(inp: InversionInput) -> InversionResult`:
  1. Keep windows with `wind_speed_m_s ≥ CALM_WIND_M_S`. If none: return `top_id=NONE`, `top_probability=0.0`, `ranked=[]`, rates `None`, `rate_at_grid_edge=False`, `inconclusive=True`, `reason="calm"`, `windows_used=0`. If fewer than `MIN_USABLE_WINDOWS`: same shape with `reason="too_few_windows"` and `windows_used` = the count.
  2. Response + log-likelihood on `RATE_GRID_KG_H / 3600`.
  3. Log prior: each candidate `ln((1 − NO_SOURCE_PRIOR)/C) − ln(Q)` per grid cell; `NONE` `ln(NO_SOURCE_PRIOR) − ln(Q)` per grid cell. Posterior over `(C+1) × Q` by log-sum-exp normalisation.
  4. Candidate probability = sum over the rate grid; rank descending (ties: by id).
  5. If the top is a source: conditional rate posterior `p[top]/Σ p[top]`; CDF over the grid; median / 5th / 95th percentiles by `np.interp(level, cdf, ln(RATE_GRID_KG_H))` then `exp`. `rate_at_grid_edge = median ≤ RATE_GRID_KG_H[1] or median ≥ RATE_GRID_KG_H[-2]`.
  6. Decision: `inconclusive=True, reason="ambiguous"` if `top_probability < MIN_CONCLUSIVE_PROBABILITY`; else, for a source top, `reason="weak_signal"` if `max(response[top] · median_kg_s) < MIN_SIGNAL_TO_NOISE · obs_sigma_ppm`; otherwise conclusive (`reason=None`). A `NONE` top has rates `None` and `rate_at_grid_edge=False`.

## Tests (full code) — `app/backend/tests/engineering/test_inversion.py`
```python
"""Tests for the Bayesian source inversion on the KS-07 layout.

Synthetic observations are generated with the SAME plume model the inversion uses, so these tests
check the algorithm only. Model mismatch is measured by the benchmark (Task 13).
"""

import time

import numpy as np

from plumetrace.engineering.dispersion import CoefficientSet
from plumetrace.engineering.geometry import Candidate, Point3, Sensor
from plumetrace.engineering.inversion import NO_SOURCE_ID, InversionInput, invert
from plumetrace.engineering.plume import concentration_ppm
from plumetrace.engineering.stability import StabilityClass
from plumetrace.facility.candidates import emission_candidates, methane_sensors
from plumetrace.facility.loader import load_facility

SPEC = load_facility()
CANDS = emission_candidates(SPEC)
SENSORS = methane_sensors(SPEC)
D = StabilityClass.D


def _receptors(sensors: list[Sensor]) -> np.ndarray:
    return np.array([[s.position.x_m, s.position.y_m, s.position.z_m] for s in sensors])


def _synth(source_id: str | None, rate_kg_h: float, windows: int = 12, seed: int = 1,
           speeds: list[float] | None = None, nan_frac: float = 0.0) -> InversionInput:
    rng = np.random.default_rng(seed)
    wind_from = 250.0 + rng.uniform(-20.0, 20.0, windows)
    obs = np.zeros((windows, len(SENSORS)))
    if source_id is not None:
        src = {c.id: c for c in CANDS}[source_id].position
        for w in range(windows):
            obs[w] = concentration_ppm(rate_kg_h / 3600.0, 4.0, float(wind_from[w]), src,
                                       _receptors(SENSORS), D, CoefficientSet.BRIGGS_RURAL,
                                       300.0, 98900.0)
    obs += rng.normal(0.0, 0.05, obs.shape)
    if nan_frac:
        obs[rng.random(obs.shape) < nan_frac] = np.nan
    return InversionInput(
        candidates=CANDS, sensors=SENSORS, observed_ppm_above_bg=obs.tolist(),
        wind_speed_m_s=speeds if speeds is not None else [4.0] * windows,
        wind_from_deg=wind_from.tolist(), stability=[D] * windows,
        temp_k=300.0, pressure_pa=98900.0,
    )


def test_recovers_vent_stack_source() -> None:
    """10 kg/h from VS-250.tip is located with high probability and the rate interval covers it."""
    r = invert(_synth("VS-250.tip", 10.0))
    assert r.top_id == "VS-250.tip"
    assert r.top_probability > 0.9
    assert r.inconclusive is False and r.reason is None
    assert r.rate_p05_kg_h is not None and r.rate_p95_kg_h is not None
    assert r.rate_p05_kg_h <= 10.0 <= r.rate_p95_kg_h
    assert r.rate_at_grid_edge is False
    assert [s.id for s in r.ranked][0] == "VS-250.tip"
    assert abs(sum(s.probability for s in r.ranked) - 1.0) < 1e-9


def test_all_calm_is_inconclusive() -> None:
    """When every window is calm the model does not apply."""
    r = invert(_synth("VS-250.tip", 10.0, speeds=[0.5] * 12))
    assert r.inconclusive is True and r.reason == "calm" and r.windows_used == 0


def test_too_few_usable_windows() -> None:
    """One usable window is not enough."""
    r = invert(_synth("VS-250.tip", 10.0, speeds=[4.0] + [0.5] * 11))
    assert r.inconclusive is True and r.reason == "too_few_windows" and r.windows_used == 1


def test_pure_noise_concludes_no_source() -> None:
    """Background-only data gives the no-source hypothesis, conclusively."""
    r = invert(_synth(None, 0.0))
    assert r.top_id == NO_SOURCE_ID
    assert r.inconclusive is False
    assert r.rate_kg_h is None


def test_mirror_symmetric_candidates_are_ambiguous() -> None:
    """Two candidates symmetric about the only sensor's line of sight cannot be separated."""
    cands = [Candidate("L", Point3(0.0, 10.0, 2.0)), Candidate("R", Point3(0.0, -10.0, 2.0))]
    sensors = [Sensor("S1", Point3(100.0, 0.0, 2.0), 0.3)]
    obs = np.array([concentration_ppm(10.0 / 3600.0, 4.0, 270.0, cands[0].position,
                                      _receptors(sensors), D, CoefficientSet.BRIGGS_RURAL,
                                      300.0, 98900.0) for _ in range(12)])
    obs += np.random.default_rng(3).normal(0.0, 0.05, obs.shape)
    r = invert(InversionInput(candidates=cands, sensors=sensors,
                              observed_ppm_above_bg=obs.tolist(), wind_speed_m_s=[4.0] * 12,
                              wind_from_deg=[270.0] * 12, stability=[D] * 12,
                              temp_k=300.0, pressure_pa=98900.0))
    assert r.inconclusive is True and r.reason == "ambiguous"


def test_missing_values_are_ignored() -> None:
    """30 % NaN observations still recover the source."""
    r = invert(_synth("VS-250.tip", 10.0, nan_frac=0.3))
    assert r.top_id == "VS-250.tip" and r.inconclusive is False


def test_leak_beyond_grid_is_flagged() -> None:
    """A 2000 kg/h leak sits at the top of the 0.1-500 kg/h grid and is flagged."""
    r = invert(_synth("VS-250.tip", 2000.0))
    assert r.top_id == "VS-250.tip"
    assert r.rate_at_grid_edge is True


def test_runtime_budget() -> None:
    """21 candidates x 80 rates x 36 windows x 8 sensors runs in under 2 s."""
    inp = _synth("VS-250.tip", 10.0, windows=36)
    start = time.perf_counter()
    invert(inp)
    assert time.perf_counter() - start < 2.0
```

## Steps
- [ ] Test → FAIL → implement (keep every function ≤ 50 lines; helpers for prior, posterior, rate quantiles, decision) → full checks green.
- [ ] **Docs.** ENGINEERING.md → "Source inversion": hypothesis space (21 candidates + no source), priors (and why `NONE` gets 0.5), rate grid, likelihood and the model-error term, decision rules with constants, outputs, limits ("candidates whose plume never reaches a sensor are indistinguishable from no source"), runtime. Work-log; `STATUS.md` (last 2.8, next 2.9).
- [ ] **Commit** `feat(engineering): add Bayesian source inversion`.
