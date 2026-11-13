"""Edge cases of the Bayesian source inversion: degenerate input, ranking ties and decision rules.

Written before the implementation (Task 8 edges). Observations come from the same plume model the
inversion uses, so these tests check the algorithm and its guards only.
"""

import math

import numpy as np
import pytest

from plumetrace.engineering.dispersion import CoefficientSet
from plumetrace.engineering.geometry import Candidate, Point3, Sensor
from plumetrace.engineering.inversion import NO_SOURCE_ID, InversionInput, _posterior, invert
from plumetrace.engineering.inversion_model import RATE_GRID_KG_H, log_likelihood
from plumetrace.engineering.plume import concentration_ppm
from plumetrace.engineering.stability import StabilityClass

D = StabilityClass.D
SRC = Point3(0.0, 0.0, 2.0)
CAND = Candidate("A", SRC)
SENSOR = Sensor("S1", Point3(300.0, 0.0, 2.0), 0.1)  # 300 m due east of the source
WIND_FROM_DEG = 270.0  # wind from the west, so the plume travels east


def _ppm(rate_kg_h: float, sensor: Sensor = SENSOR) -> float:
    """Model ppm at one sensor for a source at ``SRC``."""
    p = sensor.position
    receptor = np.array([[p.x_m, p.y_m, p.z_m]])
    conc = concentration_ppm(
        rate_kg_h / 3600.0,
        4.0,
        WIND_FROM_DEG,
        SRC,
        receptor,
        D,
        CoefficientSet.BRIGGS_RURAL,
        300.0,
        98900.0,
    )
    return float(conc[0])


def _inp(obs: list[list[float]], **kw: object) -> InversionInput:
    """Single-candidate, single-sensor input; ``kw`` overrides any field."""
    n = len(obs)
    fields: dict[str, object] = {
        "candidates": [CAND],
        "sensors": [SENSOR],
        "observed_ppm_above_bg": obs,
        "wind_speed_m_s": [4.0] * n,
        "wind_from_deg": [WIND_FROM_DEG] * n,
        "stability": [D] * n,
        "temp_k": 300.0,
        "pressure_pa": 98900.0,
    }
    fields.update(kw)
    return InversionInput.model_validate(fields)


def _noisy(rate_kg_h: float, n: int = 20, sigma: float = 0.05, seed: int = 2) -> list[list[float]]:
    rng = np.random.default_rng(seed)
    return [[_ppm(rate_kg_h) + float(rng.normal(0.0, sigma))] for _ in range(n)]


def _nan_rows(n: int) -> list[list[float]]:
    return [[math.nan] for _ in range(n)]


def test_empty_windows_is_too_few_windows() -> None:
    """No windows at all is missing data, not calm weather."""
    r = invert(_inp([]))
    assert r.inconclusive is True and r.reason == "too_few_windows" and r.windows_used == 0
    assert r.top_id == NO_SOURCE_ID and r.top_probability == 0.0 and r.ranked == []
    assert r.rate_kg_h is None and r.rate_at_grid_edge is False


def test_all_nan_observations_is_too_few_windows() -> None:
    """Windows without a single valid observation do not count as usable."""
    r = invert(_inp(_nan_rows(12)))
    assert r.inconclusive is True and r.reason == "too_few_windows" and r.windows_used == 0
    assert r.ranked == [] and r.rate_p05_kg_h is None


def test_one_window_with_data_is_too_few() -> None:
    """Only one window has observations; the other eleven are all NaN."""
    obs = _noisy(5.0, n=12)
    obs[1:] = _nan_rows(11)
    r = invert(_inp(obs))
    assert r.reason == "too_few_windows" and r.windows_used == 1


def test_nan_wind_speed_window_is_dropped() -> None:
    """A window with unknown wind speed is not used; the rest still locate the source."""
    obs = _noisy(5.0, n=12)
    r = invert(_inp(obs, wind_speed_m_s=[4.0] * 10 + [math.nan] * 2))
    assert r.windows_used == 10 and r.top_id == "A" and r.inconclusive is False


def test_nan_wind_direction_window_is_dropped() -> None:
    """A window with unknown wind direction is not used."""
    obs = _noisy(5.0, n=12)
    r = invert(_inp(obs, wind_from_deg=[math.nan] * 3 + [WIND_FROM_DEG] * 9))
    assert r.windows_used == 9 and r.top_id == "A"


def test_all_nan_wind_is_not_reported_as_calm() -> None:
    """Calm means measured and slow; unknown wind is a lack of usable windows."""
    r = invert(_inp(_noisy(5.0, n=6), wind_speed_m_s=[math.nan] * 6))
    assert r.reason == "too_few_windows" and r.windows_used == 0


def test_infinite_observation_is_ignored_like_nan() -> None:
    """An infinite reading is a sensor fault; it must not poison the posterior."""
    obs = _noisy(5.0, n=12)
    obs[0][0] = math.inf
    r = invert(_inp(obs))
    assert r.top_id == "A" and np.isfinite(r.top_probability)
    assert abs(sum(s.probability for s in r.ranked) - 1.0) < 1e-9


def test_ranking_ties_break_by_id() -> None:
    """Two candidates at the same point are exactly tied; the id decides the order."""
    cands = [Candidate("B", SRC), Candidate("A", SRC)]
    r = invert(_inp(_noisy(5.0), candidates=cands))
    assert [s.id for s in r.ranked] == ["A", "B", NO_SOURCE_ID]
    assert r.ranked[0].probability == r.ranked[1].probability
    assert r.inconclusive is True and r.reason == "ambiguous"


def test_ranked_is_descending_and_includes_no_source() -> None:
    """Every hypothesis is ranked, highest probability first."""
    r = invert(_inp(_noisy(5.0)))
    probs = [s.probability for s in r.ranked]
    assert probs == sorted(probs, reverse=True)
    assert {s.id for s in r.ranked} == {"A", NO_SOURCE_ID}


def test_single_sensor_single_candidate_recovers_rate() -> None:
    """One sensor and one candidate are enough when the source is the only suspect."""
    r = invert(_inp(_noisy(5.0)))
    assert r.top_id == "A" and r.inconclusive is False
    assert r.rate_p05_kg_h is not None and r.rate_p95_kg_h is not None
    # The model-error variance term pulls the estimate low (about 25 % here); see ENGINEERING.md.
    assert r.rate_kg_h is not None and 2.5 <= r.rate_kg_h <= 10.0
    assert r.rate_p05_kg_h <= r.rate_kg_h <= r.rate_p95_kg_h


def test_receptor_right_next_to_source_stays_finite() -> None:
    """A sensor 0.5 m downwind of the candidate gives finite numbers and a normalised posterior."""
    near = Sensor("S1", Point3(0.5, 0.0, 2.0), 0.1)
    obs = [[_ppm(5.0, near)] for _ in range(6)]
    r = invert(_inp(obs, sensors=[near]))
    assert np.isfinite(r.top_probability)
    assert abs(sum(s.probability for s in r.ranked) - 1.0) < 1e-9
    assert r.top_id == "A"


def test_unreachable_candidate_is_indistinguishable_from_no_source() -> None:
    """A candidate whose plume never reaches a sensor ties with no source: inconclusive."""
    upwind = Sensor("S1", Point3(-300.0, 0.0, 2.0), 0.1)
    rng = np.random.default_rng(4)
    obs = rng.normal(0.0, 0.05, (12, 1)).tolist()
    r = invert(_inp(obs, sensors=[upwind]))
    assert r.inconclusive is True and r.reason == "ambiguous"
    assert {s.id for s in r.ranked[:2]} == {"A", NO_SOURCE_ID}
    assert r.top_probability == pytest.approx(0.5, abs=1e-9)


def test_weak_signal_is_flagged() -> None:
    """Conclusive evidence from many windows, but no reading above 3 sigma, is a weak signal."""
    rate_kg_h = 0.2 / _ppm(1.0)  # peak response 0.2 ppm = 2 sigma_obs
    rng = np.random.default_rng(5)
    obs = [[_ppm(rate_kg_h) + float(rng.normal(0.0, 0.1))] for _ in range(60)]
    r = invert(_inp(obs))
    assert r.top_id == "A" and r.top_probability >= 0.6
    assert r.inconclusive is True and r.reason == "weak_signal"
    assert r.rate_kg_h is not None  # the estimate is still reported


def test_rate_at_low_edge_is_flagged() -> None:
    """A leak below the bottom of the grid pins the posterior to the grid edge."""
    obs = [[_ppm(0.03)] for _ in range(20)]
    r = invert(_inp(obs, obs_sigma_ppm=1e-4, model_rel_error=0.05))
    assert r.top_id == "A" and r.rate_at_grid_edge is True
    assert r.rate_kg_h is not None and r.rate_kg_h <= float(RATE_GRID_KG_H[1])


def test_candidate_order_does_not_change_the_answer() -> None:
    """Reversing the candidate list gives the same ranking and rate."""
    far = Candidate("F", Point3(-50.0, 40.0, 6.0))
    obs = _noisy(5.0)
    a = invert(_inp(obs, candidates=[CAND, far]))
    b = invert(_inp(obs, candidates=[far, CAND]))
    assert [s.id for s in a.ranked] == [s.id for s in b.ranked]
    assert a.rate_kg_h == pytest.approx(b.rate_kg_h)


_BAD_INPUTS = [
    pytest.param({"candidates": []}, id="no_candidates"),
    pytest.param({"sensors": []}, id="no_sensors"),
    pytest.param({"candidates": [Candidate("NONE", SRC)]}, id="candidate_named_none"),
    pytest.param({"candidates": [CAND, CAND]}, id="duplicate_ids"),
    pytest.param({"obs_sigma_ppm": 0.0}, id="zero_sigma"),
    pytest.param({"obs_sigma_ppm": -0.1}, id="negative_sigma"),
    pytest.param({"model_rel_error": -0.1}, id="negative_model_error"),
    pytest.param({"temp_k": 0.0}, id="zero_temp"),
    pytest.param({"pressure_pa": -1.0}, id="negative_pressure"),
    pytest.param({"wind_speed_m_s": [4.0] * 5}, id="short_speed"),
    pytest.param({"wind_from_deg": [270.0] * 7}, id="long_direction"),
    pytest.param({"stability": [D] * 3}, id="short_stability"),
    pytest.param({"observed_ppm_above_bg": [[0.0, 0.0]] * 6}, id="row_width"),
    pytest.param({"observed_ppm_above_bg": [[1e160]] * 6}, id="obs_above_pure_methane"),
    pytest.param({"observed_ppm_above_bg": [[-1.5e6]] * 6}, id="obs_below_minus_pure_methane"),
    pytest.param({"wind_speed_m_s": [-1.0] * 6}, id="negative_speed"),
]


@pytest.mark.parametrize("kw", _BAD_INPUTS)
def test_bad_input_is_rejected(kw: dict[str, object]) -> None:
    """Shape and value errors raise ValueError instead of returning a number."""
    with pytest.raises(ValueError):
        _inp([[0.0]] * 6, **kw)


def test_log_likelihood_all_nan_is_zero() -> None:
    """With no valid observation every hypothesis has the same (zero) log-likelihood."""
    response = np.ones((2, 3, 1))
    ll = log_likelihood(np.full((3, 1), np.nan), response, np.array([1e-3, 2e-3]), 0.1, 0.6)
    assert ll.shape == (3, 2)
    assert np.all(ll == 0.0)


def test_known_zero_wind_is_calm() -> None:
    """A measured wind speed of exactly zero in every window is calm."""
    r = invert(_inp(_noisy(5.0, n=6), wind_speed_m_s=[0.0] * 6))
    assert r.reason == "calm" and r.inconclusive is True and r.windows_used == 0


def test_calm_mixed_with_unknown_wind_is_too_few_windows() -> None:
    """Calm windows plus windows with unknown wind: not every wind is known, so not calm."""
    r = invert(_inp(_noisy(5.0, n=12), wind_speed_m_s=[0.5] * 6 + [math.nan] * 6))
    assert r.reason == "too_few_windows" and r.windows_used == 0


@pytest.mark.parametrize("value", [1.0e6, -1.0e6])
def test_pure_methane_bound_is_accepted(value: float) -> None:
    """The bound is inclusive and a reading at the bound gives a finite, normalised posterior."""
    r = invert(_inp([[value]] * 6))
    assert math.isfinite(r.top_probability)
    assert abs(sum(s.probability for s in r.ranked) - 1.0) < 1e-9


def test_nonphysical_observation_message() -> None:
    """The rejection names the bound so the caller can see what is wrong."""
    with pytest.raises(ValueError, match="within -1e6 and 1e6 ppm"):
        _inp([[1e160]] * 6)


@pytest.mark.parametrize(
    "bad", [np.full((2, 80), -np.inf), np.where(np.eye(2, 80) > 0, np.nan, 0.0)]
)
def test_non_finite_posterior_fails_visibly(bad: np.ndarray) -> None:
    """A non-finite log-posterior raises instead of returning a made-up distribution."""
    with pytest.raises(ValueError, match="posterior is not finite"):
        _posterior(bad)
